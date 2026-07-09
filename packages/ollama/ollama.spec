%global debug_package %{nil}
%global __provides_exclude_from ^%{_prefix}/lib/ollama/.*$
%global __requires_exclude_from ^%{_prefix}/lib/ollama/.*$

Name:           ollama
Version:        0.31.2
Release:        2%{?dist}
Summary:        Local LLM runner and API server

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        %{name}-%{version}-x86_64.tar.zst
Source1:        %{name}-%{version}-aarch64.tar.zst
Source2:        %{name}-%{version}-docs.tar.gz

BuildRequires:  zstd
BuildRequires:  systemd-rpm-macros
Requires(pre):  shadow-utils
%{?systemd_requires}

ExclusiveArch:  aarch64 x86_64

%description
Ollama runs large language models locally and exposes a command-line interface
and local API server.

%prep
%setup -q -T -c -n %{name}-%{version}
tar -xzf %{SOURCE2}
%ifarch x86_64
tar --zstd -xf %{SOURCE0}
%endif
%ifarch aarch64
tar --zstd -xf %{SOURCE1}
%endif

%install
install -Dpm0755 bin/ollama %{buildroot}%{_bindir}/ollama
install -d %{buildroot}%{_prefix}/lib
cp -a lib/ollama %{buildroot}%{_prefix}/lib/
install -d %{buildroot}%{_unitdir}
cat > %{buildroot}%{_unitdir}/ollama.service <<'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=default.target
EOF
# Upstream binaries can include "$ORIGIN:/build/llama-server-cpu/bin:".
# Terminate the dynamic-string entry after "$ORIGIN" so check-rpaths only sees
# the valid sibling-library lookup path.
find %{buildroot}%{_prefix}/lib/ollama -type f -name '*.so' -exec sh -c '
for file; do
  offsets="$(LC_ALL=C grep -aobF ":/build/llama-server-cpu/bin:" "$file" 2>/dev/null | cut -d: -f1 || true)"
  for offset in $offsets; do
    printf "\000" | dd of="$file" bs=1 seek="$offset" count=1 conv=notrunc status=none
  done
done
' sh {} +

%check
%{buildroot}%{_bindir}/ollama --version >/dev/null

%pre
if ! id ollama >/dev/null 2>&1; then
    useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
fi
exit 0

%post
if getent group render >/dev/null 2>&1; then
    usermod -a -G render ollama || :
fi
if getent group video >/dev/null 2>&1; then
    usermod -a -G video ollama || :
fi
%systemd_post ollama.service

%preun
%systemd_preun ollama.service

%postun
%systemd_postun_with_restart ollama.service

%files
%license LICENSE
%doc README.md
%{_unitdir}/ollama.service
%{_bindir}/ollama
%{_prefix}/lib/ollama/

%changelog
* Thu Jul 09 2026 Bahram Farahmand <bahram.0098.bf@gmail.com> - 0.31.2-2
- Align ollama system user creation with upstream install script

* Thu Jul 09 2026 Codex Automation <noreply@users.noreply.github.com> - 0.31.2-1
- Update to v0.31.2

* Wed Jul 01 2026 Codex Automation <noreply@users.noreply.github.com> - 0.31.1-1
- Update to v0.31.1

* Wed Jul 01 2026 Bahram Farahmand <bahram.0098.bf@gmail.com> - 0.30.11-2
- Add systemd service unit for ollama

* Sat Jun 27 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.11-1
- Update to v0.30.11

* Thu Jun 18 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.10-1
- Update to v0.30.10

* Wed Jun 17 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.9-1
- Update to v0.30.9

* Fri Jun 12 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.8-1
- Update to v0.30.8

* Thu Jun 11 2026 matt haigh <matthaigh27@gmail.com> - 0.30.7-2
- Rebuild to recover failed Copr repository generation on fedora-rawhide-aarch64

* Tue Jun 09 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.7-1
- Update to v0.30.7

* Sat Jun 06 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.6-1
- Update to v0.30.6

* Fri Jun 05 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.5-1
- Update to v0.30.5

* Thu Jun 04 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.4-1
- Update to v0.30.4

* Thu Jun 04 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.2-2
- Normalize bundled shared-library RUNPATHs

* Wed Jun 03 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.2-1
- Update to v0.30.2

* Tue Jun 02 2026 Codex Automation <noreply@users.noreply.github.com> - 0.30.0-1
- Update to v0.30.0

* Fri May 15 2026 Codex Automation <noreply@users.noreply.github.com> - 0.24.0-1
- Update to v0.24.0

* Thu May 14 2026 Codex Automation <noreply@users.noreply.github.com> - 0.23.4-1
- Update to v0.23.4

* Wed May 13 2026 Codex Automation <noreply@users.noreply.github.com> - 0.23.3-1
- Update to v0.23.3

* Fri May 08 2026 Codex Automation <noreply@users.noreply.github.com> - 0.23.2-1
- Update to v0.23.2

* Wed May 06 2026 Codex Automation <noreply@users.noreply.github.com> - 0.23.1-1
- Update to v0.23.1

* Sun May 03 2026 Codex Automation <noreply@users.noreply.github.com> - 0.23.0-1
- Update to v0.23.0

* Thu Apr 30 2026 Codex Automation <noreply@users.noreply.github.com> - 0.22.1-1
- Update to v0.22.1

* Wed Apr 29 2026 Codex Automation <noreply@users.noreply.github.com> - 0.22.0-1
- Update to v0.22.0

* Fri Apr 24 2026 Codex Automation <noreply@users.noreply.github.com> - 0.21.2-1
- Update to v0.21.2

* Wed Apr 22 2026 Codex Automation <noreply@users.noreply.github.com> - 0.21.1-1
- Update to v0.21.1

* Fri Apr 17 2026 Codex Automation <noreply@users.noreply.github.com> - 0.21.0-1
- Update to v0.21.0

* Tue Apr 14 2026 Codex Automation <noreply@users.noreply.github.com> - 0.20.7-1
- Update to v0.20.7

* Mon Apr 13 2026 Codex Automation <noreply@users.noreply.github.com> - 0.20.6-1
- Update to v0.20.6

* Sun Apr 12 2026 Codex Automation <noreply@users.noreply.github.com> - 0.20.5-1
- Initial COPR packaging for Ollama
