%global debug_package %{nil}
%global nodejs_major 25
%global npm_version 11.12.1

# V8/cppgc bundles hand-written assembly (e.g. the PushAllRegistersAndIterateStack
# stack-scanning trampoline) that breaks under the distro-default -flto: gcc's LTO
# ltrans stage re-emits the asm symbol across partitions and fails with
# "symbol ... is already defined". V8 does its own optimization; disable RPM LTO.
%global _lto_cflags %{nil}

Name:           nodejs25-caged
Version:        25.9.0
Release:        9%{?dist}
Summary:        Node.js 25 built with V8 pointer compression

License:        MIT
URL:            https://nodejs.org/
Source0:        https://nodejs.org/dist/v%{version}/node-v%{version}.tar.xz
Source1:        https://nodejs.org/dist/v%{version}/SHASUMS256.txt

BuildRequires:  findutils
BuildRequires:  libatomic
BuildRequires:  make
BuildRequires:  python3
BuildRequires:  tar
BuildRequires:  xz
%if 0%{?amzn}
# AL2023's default gcc (11) and clang (15) are both too old for Node 25's
# C++20 deps; gcc 14 ships as a co-installable namespaced package.
BuildRequires:  gcc14
BuildRequires:  gcc14-c++
%else
BuildRequires:  clang
BuildRequires:  gcc-c++
%endif
%if 0%{?fedora} >= 45
# Node 25's configure rejects Python > 3.14; rawhide defaults to 3.15.
BuildRequires:  python3.14
%endif

Provides:       node = %{version}-%{release}
Provides:       nodejs = %{version}-%{release}
Provides:       nodejs%{nodejs_major} = %{version}-%{release}
Provides:       nodejs-npm = %{npm_version}
Provides:       nodejs-npx = %{npm_version}
Provides:       nodejs%{nodejs_major}-npm = %{npm_version}
Provides:       nodejs%{nodejs_major}-npx = %{npm_version}
Provides:       npm = %{npm_version}
Provides:       npx = %{npm_version}

# This package bundles its own npm and now ships /etc/npmrc, which the distro's
# nodejs-npm subpackage also owns -- co-installing the two would hit an rpm file
# conflict on /etc/npmrc (and on /usr/bin/npm). rpm ignores a Conflicts satisfied
# only by the package's own Provides, so this blocks the real nodejs-npm without
# self-conflicting on the nodejs-npm capability we provide above.
Conflicts:      nodejs-npm

ExclusiveArch:  aarch64 x86_64

%description
Node.js 25 built from the official source tarball with V8 pointer compression
enabled.

%prep
%setup -q -n node-v%{version}

%build
# Node 25 bundles a V8 and an ada URL parser that need a modern C++20 toolchain:
# gcc >= 12 or clang >= 19. ada uses constexpr std::string that only gcc >= 12
# accepts; V8 uses C++20 implicit-typename syntax (P0634, "Down with typename!")
# that needs clang >= 16; and V8 25's regexp bytecode tables use consteval that
# clang only compiles at >= 19 (clang 16-18 reject them with "call to immediate
# function ... is not a constant expression"). So clang 15 + gcc 11 (Amazon
# Linux 2023) and clang 18 (Azure Linux 3) each fail in a different way.
%if 0%{?amzn}
# AL2023: use the co-installable gcc 14 (default gcc 11 / clang 15 are too old).
export CC=gcc14-gcc CXX=gcc14-g++
%else
%if 0%{?azl}
# Azure Linux 3 ships clang 18, which rejects V8 25's regexp bytecode tables
# with "call to immediate function ... is not a constant expression" (a stricter
# consteval diagnostic that newer clang on Fedora/EL does not raise). Its default
# gcc 13 builds Node 25's C++20 deps fine, so force gcc here. NOTE: this is only
# a fast-path -- COPR's azure-linux-3 buildroot does not always define %%{?azl}
# (mock injects %%dist but not the azl macro), so the clang >= 19 check below is
# the real safety net that keeps Azure Linux 3 off its too-old clang 18.
export CC=gcc CXX=g++
%else
# Elsewhere pick the compiler at build time: prefer clang only when it is new
# enough for V8 25 (>= 19; clang 16-18 miscompile V8's consteval regexp tables),
# otherwise fall back to gcc (>= 12 builds the C++20 deps fine). This >= 19 gate
# also catches Azure Linux 3 (clang 18, gcc 13) whenever the %%{?azl} fast-path
# above does not fire. Detect the major version via the predefined macro rather
# than `clang -dumpversion`, which has historically reported a faked gcc-compat
# version.
clang_major="$(echo __clang_major__ | clang -E -P -x c - 2>/dev/null | tr -d '[:space:]')"
if [ "${clang_major:-0}" -ge 19 ]; then
    export CC=clang CXX=clang++
else
    export CC=gcc CXX=g++
fi
%endif
%endif
%{?set_build_flags}

%if 0%{?amzn}
# Amazon Linux rpm macros add the annobin spec, but the gcc14 packages do not
# provide a matching annobin plugin in gcc14's plugin path.
for _var in CFLAGS CXXFLAGS FFLAGS FCFLAGS LDFLAGS; do
    eval "_value=\${${_var}:-}"
    _value="$(printf '%s' "$_value" | sed -E 's@ *-specs=[^ ]*annobin[^ ]*@@g')"
    export "${_var}=${_value}"
done
%endif

# Belt-and-suspenders LTO scrub. V8/cppgc bundles hand-written assembly (the
# PushAllRegistersAndIterateStack stack-scanning trampoline) that breaks under
# -flto: gcc's LTO ltrans partitioning stage re-emits the asm symbol across
# partitions and fails the assembler with "symbol ... is already defined". The
# %%global _lto_cflags %%{nil} above removes the flag where it comes from RPM's
# _lto_cflags (Amazon Linux 2023), but in case any -flto reaches the effective
# flags by another path, strip every -flto/-ffat-lto-objects token here too.
# This is a no-op when no LTO flag is present (e.g. the clang chroots and Azure
# Linux 3, whose default flags carry no -flto). Keep in sync with the %%install
# copy, where `make install` re-links host tools in a fresh shell. The pattern
# matches -flto, -flto=auto, -ffat-lto-objects and -fno-lto while leaving other
# -f... flags intact.
for _var in CFLAGS CXXFLAGS FFLAGS FCFLAGS LDFLAGS; do
    eval "_value=\${${_var}:-}"
    _value="$(printf '%s' "$_value" | sed -E 's@ *-f(no-)?(fat-)?lto([=-][^ ]*)?@@g')"
    export "${_var}=${_value}"
done

# Some toolchains (notably EL's gcc-toolset ld) ship only the versioned
# libatomic.so.1 runtime, not the unversioned libatomic.so linker symlink, so
# Node's `-latomic` helper targets fail to link with "cannot find -latomic".
# Provide a local symlink and point compiler driver library discovery at it;
# Node's build does not propagate LDFLAGS into every host-tool link. The same
# block runs again in %%install, where `make install` re-links the node_js2c
# host tool in a fresh shell -- keep the two copies in sync.
atomic_lib="$(ls /usr/lib64/libatomic.so.1 /usr/lib/libatomic.so.1 2>/dev/null | head -n1)"
if [ -n "$atomic_lib" ]; then
    mkdir -p %{_builddir}/atomic-shim
    ln -sf "$atomic_lib" %{_builddir}/atomic-shim/libatomic.so
    export LIBRARY_PATH="%{_builddir}/atomic-shim${LIBRARY_PATH:+:$LIBRARY_PATH}"
    export LDFLAGS="${LDFLAGS:-} -L%{_builddir}/atomic-shim"
fi

# Node 25's configure rejects Python newer than 3.14 (Fedora rawhide ships
# 3.15). Use the newest interpreter in the supported range and make the build
# (gyp) use it too.
for _py in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$_py" >/dev/null 2>&1; then
        PYTHON="$(command -v "$_py")"
        break
    fi
done
export PYTHON
"$PYTHON" configure \
    --prefix=%{_prefix} \
    --experimental-enable-pointer-compression
%make_build

%install
# rpm runs each section in its own shell, so the libatomic shim and the
# LIBRARY_PATH/LDFLAGS exports from %%build are gone here. Node's `install`
# target depends on `all`, which re-links the node_js2c host tool with a bare
# `-latomic`, so without re-establishing the shim the install fails with
# "cannot find -latomic" on EL/Amazon Linux. Keep in sync with the %%build copy.
atomic_lib="$(ls /usr/lib64/libatomic.so.1 /usr/lib/libatomic.so.1 2>/dev/null | head -n1)"
if [ -n "$atomic_lib" ]; then
    mkdir -p %{_builddir}/atomic-shim
    ln -sf "$atomic_lib" %{_builddir}/atomic-shim/libatomic.so
    export LIBRARY_PATH="%{_builddir}/atomic-shim${LIBRARY_PATH:+:$LIBRARY_PATH}"
    export LDFLAGS="${LDFLAGS:-} -L%{_builddir}/atomic-shim"
fi

%if 0%{?amzn}
# `make install` depends on `all` and recompiles sources in this fresh shell,
# whose CFLAGS/CXXFLAGS carry Amazon Linux's injected annobin spec (rpm exports
# the hardened flags into every section's environment) -- but the gcc14 packages
# provide no matching annobin plugin, so gcc14-g++ aborts with "inaccessible
# plugin file plugin/annobin.so". The %%build annobin strip does not carry over
# here, so mirror it: drop every -specs=*annobin* token. Keep in sync with
# %%build.
for _var in CFLAGS CXXFLAGS FFLAGS FCFLAGS LDFLAGS; do
    eval "_value=\${${_var}:-}"
    _value="$(printf '%s' "$_value" | sed -E 's@ *-specs=[^ ]*annobin[^ ]*@@g')"
    export "${_var}=${_value}"
done
%endif

# `make install` depends on `all` and re-links host tools, so mirror the %%build
# LTO scrub here too: strip any -flto/-ffat-lto-objects token that would
# re-trigger the V8 cppgc "PushAllRegistersAndIterateStack already defined"
# assembler failure. No-op when no LTO flag is present. Keep in sync with %%build.
for _var in CFLAGS CXXFLAGS FFLAGS FCFLAGS LDFLAGS; do
    eval "_value=\${${_var}:-}"
    _value="$(printf '%s' "$_value" | sed -E 's@ *-f(no-)?(fat-)?lto([=-][^ ]*)?@@g')"
    export "${_var}=${_value}"
done
%make_install PREFIX=%{_prefix}

# Ship the same npm distribution config as Fedora's official nodejs-npm package.
# Node's bundled npm, with no config, derives its global prefix from the parent
# of the node binary's directory -- i.e. %{_prefix} (/usr) -- so `npm install -g`
# writes into the rpm-managed /usr/lib/node_modules and fails with EACCES for
# non-root users (and would clobber package-owned files as root). The official
# package avoids this by shipping a builtin npmrc (at the root of the npm module
# dir) that only redirects globalconfig to /etc/npmrc, then setting the real
# prefix to /usr/local -- the standard local-admin tree -- in that one editable
# file. Mirror both files here so this build behaves like stock distro Node.
cat > %{buildroot}%{_prefix}/lib/node_modules/npm/npmrc <<'EOF'
# Distribution-level npm configuration. Do not edit; put system-wide settings in
# the globalconfig file below (defaults to /etc/npmrc).
# vim:set filetype=dosini:

globalconfig=/etc/npmrc
EOF
mkdir -p %{buildroot}%{_sysconfdir}
cat > %{buildroot}%{_sysconfdir}/npmrc <<'EOF'
prefix=/usr/local
python=/usr/bin/python3
update-notifier=false
EOF

%check
# Run node directly on the npm/npx cli scripts: their shebang is the absolute
# install path (%{_bindir}/node), which does not exist yet at %%check time --
# only the buildroot copy does -- so invoking the symlinks would fail with
# "bad interpreter".
node_bin="%{buildroot}%{_bindir}/node"
npm_dir="%{buildroot}%{_prefix}/lib/node_modules/npm/bin"
"$node_bin" --version | grep -qx "v%{version}"
"$node_bin" -p "process.config.variables.v8_enable_pointer_compression" | grep -qx "1"
"$node_bin" "$npm_dir/npm-cli.js" --version | grep -qx "%{npm_version}"
"$node_bin" "$npm_dir/npx-cli.js" --version >/dev/null

%files
%license LICENSE
%doc README.md
%config(noreplace) %{_sysconfdir}/npmrc
%{_bindir}/node
%{_bindir}/npm
%{_bindir}/npx
%{_includedir}/node
%{_prefix}/lib/node_modules/npm
%{_datadir}/doc/node
%{_mandir}/man1/node.1*

%changelog
* Wed Jun 17 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-9
- Ship npm distribution config matching Fedora's official nodejs-npm: a builtin
  npmrc (in the npm module dir) redirecting globalconfig to /etc/npmrc, plus
  /etc/npmrc setting prefix=/usr/local. Without these, bundled npm derived its
  global prefix from the node binary path (%%{_prefix}=/usr), so `npm install -g`
  hit EACCES on the rpm-managed /usr/lib/node_modules for non-root users. Now
  global installs land in /usr/local like stock distro Node
- Add Conflicts: nodejs-npm so the distro npm (which also owns /etc/npmrc) cannot
  co-install and trigger an rpm file conflict

* Sat Jun 15 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-8
- Fix amazonlinux-2023 (x86_64 and aarch64) %%install failure: `make install`
  depends on `all` and recompiles sources in a fresh shell where the build flags
  are re-derived WITH Amazon Linux's injected annobin spec. gcc14 provides no
  matching annobin plugin, so the install recompile aborted with "inaccessible
  plugin file plugin/annobin.so". The %%build section already strips
  -specs=*annobin* but that env did not carry into %%install (only the LTO scrub
  and libatomic shim were mirrored there). Mirror the annobin strip into
  %%install too, kept in sync with %%build
- Raise the per-package COPR build timeout from 43200s (12h) to 108000s (30h,
  Copr's maximum) in packages.json for azure-linux-3-aarch64: that chroot's
  slower aarch64 builder hit the 12h timeout still mid-%%build (compiling the
  bundled LIEF dependency, before the V8/node link) and was killed with
  "Copr timeout => sending INT". azure-linux-3-x86_64 succeeds, so this is
  builder-speed/arch specific, not a build defect

* Mon Jun 15 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-7
- Fix amazonlinux-2023 link failure: disable RPM's injected LTO
  (%%global _lto_cflags %%{nil}, plus a belt-and-suspenders -flto scrub).
  V8/cppgc's hand-written push_registers asm (PushAllRegistersAndIterateStack)
  breaks under gcc's -flto=auto, whose ltrans partitioning stage re-emits the
  asm symbol in more than one partition and fails the assembler with
  "symbol `PushAllRegistersAndIterateStack' is already defined". V8 does its own
  optimization so dropping the distro-default LTO is safe
- Actually keep Azure Linux 3 off clang 18: the 25.9.0-6 %%{?azl} gcc-switch
  never fired because COPR's azure-linux-3 buildroot does not define the azl
  macro (mock injects %%dist but not %%azl), so the build fell back to clang 18
  and failed compiling V8 25's regexp consteval bytecode tables. Raise the
  clang-fallback threshold from >= 16 to >= 19 (V8 25's real minimum) so clang
  18 falls back to gcc 13 regardless of whether the %%{?azl} fast-path fires

* Sat Jun 13 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-6
- Fix the annobin-spec strip on Amazon Linux: the sed targeted
  /usr/lib/rpm/redhat-annobin-cc1 but the real flag is
  /usr/lib/rpm/redhat/redhat-annobin-cc1, so the strip was a no-op and gcc14
  still failed with "inaccessible plugin file plugin/annobin.so". Match any
  -specs=*annobin* token instead
- Build with gcc on Azure Linux 3: its clang 18 rejects V8 25's regexp consteval
  bytecode tables ("call to immediate function ... is not a constant
  expression"); gcc 13 compiles the C++20 deps cleanly

* Fri Jun 12 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-5
- Re-establish the libatomic shim in %%install: rpm runs each section in its own
  shell, and `make install` re-links the node_js2c host tool, so the %%build env
  was lost and EL/Amazon Linux failed with "cannot find -latomic" during install

* Thu Jun 11 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-4
- Make the libatomic shim visible via LIBRARY_PATH so Node's host-tool links
  find -latomic even when LDFLAGS is not propagated
- Strip the annobin rpm spec on Amazon Linux when building with gcc14, whose
  plugin path does not contain annobin.so

* Wed Jun 10 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-3
- Amazon Linux 2023: build with the co-installable gcc 14 (gcc14-g++); its
  default gcc 11 and clang 15 are both too old for Node 25's C++20 deps (ada's
  constexpr std::string and V8's implicit-typename respectively)
- Fix %%check on Fedora: invoke node directly on npm-cli.js/npx-cli.js instead
  of the symlinks, whose absolute /usr/bin/node shebang is absent at check time
- Fix "cannot find -latomic" link failures on EL by shimming the unversioned
  libatomic.so where only libatomic.so.1 is shipped
- Select a Python <= 3.14 for configure/gyp so the build works on Fedora
  rawhide (which ships Python 3.15)
- Fix bogus changelog date

* Tue Jun 09 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-2
- Prefer clang but fall back to gcc when clang < 16, so V8's C++20
  implicit-typename code compiles on chroots with older clang (e.g. clang 15
  on Amazon Linux 2023)

* Thu Jun 04 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-1
- Initial COPR packaging for Node.js 25 with V8 pointer compression
