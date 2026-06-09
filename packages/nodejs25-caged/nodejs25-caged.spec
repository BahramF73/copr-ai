%global debug_package %{nil}
%global nodejs_major 25
%global npm_version 11.12.1

Name:           nodejs25-caged
Version:        25.9.0
Release:        2%{?dist}
Summary:        Node.js 25 built with V8 pointer compression

License:        MIT
URL:            https://nodejs.org/
Source0:        https://nodejs.org/dist/v%{version}/node-v%{version}.tar.xz
Source1:        https://nodejs.org/dist/v%{version}/SHASUMS256.txt

BuildRequires:  clang
BuildRequires:  findutils
BuildRequires:  gcc-c++
BuildRequires:  libatomic
BuildRequires:  make
BuildRequires:  python3
BuildRequires:  tar
BuildRequires:  xz

Provides:       node = %{version}-%{release}
Provides:       nodejs = %{version}-%{release}
Provides:       nodejs%{nodejs_major} = %{version}-%{release}
Provides:       nodejs-npm = %{npm_version}
Provides:       nodejs-npx = %{npm_version}
Provides:       nodejs%{nodejs_major}-npm = %{npm_version}
Provides:       nodejs%{nodejs_major}-npx = %{npm_version}
Provides:       npm = %{npm_version}
Provides:       npx = %{npm_version}

ExclusiveArch:  aarch64 x86_64

%description
Node.js 25 built from the official source tarball with V8 pointer compression
enabled.

%prep
%setup -q -n node-v%{version}

%build
# Prefer clang, but fall back to gcc where clang is too old. Node 25 bundles a
# V8 that uses C++20 implicit-typename syntax (P0634, "Down with typename!"),
# which only clang >= 16 accepts; clang 15 (e.g. Amazon Linux 2023) fails to
# compile V8 with "missing 'typename' prior to dependent type name". Detect the
# major version via the predefined macro rather than `clang -dumpversion`, which
# has historically reported a faked gcc-compat version.
clang_major="$(echo __clang_major__ | clang -E -P -x c - 2>/dev/null | tr -d '[:space:]')"
if [ "${clang_major:-0}" -ge 16 ]; then
    export CC=clang CXX=clang++
else
    export CC=gcc CXX=g++
fi
%{?set_build_flags}
./configure \
    --prefix=%{_prefix} \
    --experimental-enable-pointer-compression
%make_build

%install
%make_install PREFIX=%{_prefix}

%check
export PATH="%{buildroot}%{_bindir}:$PATH"
%{buildroot}%{_bindir}/node --version | grep -qx "v%{version}"
%{buildroot}%{_bindir}/node -p "process.config.variables.v8_enable_pointer_compression" | grep -qx "1"
%{buildroot}%{_bindir}/npm --version | grep -qx "%{npm_version}"
%{buildroot}%{_bindir}/npx --version >/dev/null

%files
%license LICENSE
%doc README.md
%{_bindir}/node
%{_bindir}/npm
%{_bindir}/npx
%{_includedir}/node
%{_prefix}/lib/node_modules/npm
%{_datadir}/doc/node
%{_mandir}/man1/node.1*

%changelog
* Mon Jun 09 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-2
- Prefer clang but fall back to gcc when clang < 16, so V8's C++20
  implicit-typename code compiles on chroots with older clang (e.g. clang 15
  on Amazon Linux 2023)

* Thu Jun 04 2026 matt haigh <matthaigh27@gmail.com> - 25.9.0-1
- Initial COPR packaging for Node.js 25 with V8 pointer compression
