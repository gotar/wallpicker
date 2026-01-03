# Maintainer: pgotar <pgotar@users.noreply.github.com>
pkgname=wallpicker
pkgver=1.0
pkgrel=1
pkgdesc="Modern GTK4/Libadwaita wallpaper picker with Wallhaven integration"
arch=('any')
url="https://github.com/gotar/wallpicker"
license=('MIT')
depends=(
  'python>=3.11'
  'python-gobject'
  'gtk4'
  'libadwaita'
  'python-requests'
  'python-pillow'
  'python-send2trash'
  'python-aiohttp'
  'python-rapidfuzz'
)
makedepends=('python-setuptools' 'git')
optdepends=('awww: Animated wallpaper transitions')
source=("${pkgname}::git+https://github.com/gotar/wallpicker.git#tag=v${pkgver}")
sha256sums=('SKIP')

prepare() {
  cd "${srcdir}/${pkgname}"
}

package() {
  cd "${srcdir}/${pkgname}"

  # Install source files
  install -d "${pkgdir}/usr/share/${pkgname}"
  cp -r src "${pkgdir}/usr/share/${pkgname}/"
  cp -r data "${pkgdir}/usr/share/${pkgname}/"

  # Install main entry point
  install -Dm755 main.py "${pkgdir}/usr/share/${pkgname}/main.py"

  # Create launcher script
  cat > "${pkgdir}/usr/share/${pkgname}/wallpicker" << EOF
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/usr/share/wallpicker')
os.chdir('/usr/share/wallpicker')
from main import main
if __name__ == '__main__':
    main()
EOF
  chmod +x "${pkgdir}/usr/share/${pkgname}/wallpicker"

  # Create symlink in /usr/bin
  install -d "${pkgdir}/usr/bin"
  ln -s "/usr/share/${pkgname}/wallpicker" "${pkgdir}/usr/bin/wallpicker"

  # Install desktop entry
  install -Dm644 wallpicker.desktop "${pkgdir}/usr/share/applications/wallpicker.desktop"
  sed -i 's|Exec=/home/gotar/Programowanie/wallpicker/launcher.sh|Exec=/usr/bin/wallpicker|g' "${pkgdir}/usr/share/applications/wallpicker.desktop"
  sed -i 's|Icon=/home/gotar/Programowanie/wallpicker/data/wallpaper-icon.svg|Icon=/usr/share/wallpicker/data/wallpaper-icon.svg|g' "${pkgdir}/usr/share/applications/wallpicker.desktop"

  # Install icon
  install -Dm644 data/wallpaper-icon.svg "${pkgdir}/usr/share/wallpicker/data/wallpaper-icon.svg"
  install -d "${pkgdir}/usr/share/icons/hicolor/scalable/apps"
  ln -s "/usr/share/wallpicker/data/wallpaper-icon.svg" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/wallpicker.svg"

  # Install documentation
  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"

  # Install license if it exists
  if [ -f LICENSE ]; then
    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
  fi

  # Clean up development files
  rm -f "${pkgdir}/usr/share/${pkgname}/launcher.py"
  rm -f "${pkgdir}/usr/share/${pkgname}/launcher.sh"
  rm -rf "${pkgdir}/usr/share/${pkgname}/tests"
  rm -f "${pkgdir}/usr/share/${pkgname}/install.sh"
  rm -f "${pkgdir}/usr/share/${pkgname}/.SRCINFO"
  rm -f "${pkgdir}/usr/share/${pkgname}/.gitignore"
  rm -rf "${pkgdir}/usr/share/${pkgname}/.git"
  rm -f "${pkgdir}/usr/share/${pkgname}/mise.toml"
  rm -f "${pkgdir}/usr/share/${pkgname}/PKGBUILD"
  rm -f "${pkgdir}/usr/share/${pkgname}/README.md"
}
