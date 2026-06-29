SHELL := /bin/sh

.PHONY: srpm

srpm:
	dnf -y install curl git rpm-build
	UPSTREAM_URL="https://github.com/ComposioHQ/composio.git" \
	UPSTREAM_TAG_PREFIX="@composio/cli@" \
	PACKAGE_NAME="composio" \
	RELEASE_ASSET_X86_64="composio-linux-x64.zip" \
	RELEASE_ASSET_AARCH64="composio-linux-aarch64.zip" \
	DOC_FILES="LICENSE README.md" \
	../../scripts/make_binary_release_srpm.sh --spec "$(spec)" --outdir "$(outdir)"
