# Maintainer: pgotar <pgotar@users.noreply.github.com>
pkgname=wallpicker
pkgver=1.1.1
pkgrel=1
pkgdesc="Modern GTK4/Libadwaita wallpaper picker with Wallhaven integration"
arch=('any')
url="https://github.com/gotar/wallpicker"
license=('MIT')
depends=(
  'python>=3.11'
  'gtk4'
  'libadwaita'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'git')
optdepends=('awww: Animated wallpaper transitions')
source=("${pkgname}::git+https://github.com/gotar/wallpicker.git#tag=v${pkgver}")
sha256sums=('SKIP')

build() {
  cd "${srcdir}/${pkgname}"
  python -m build
}

package() {
  cd "${srcdir}/${pkgname}"

  # Install Python package
  python -m installer --destdir="$pkgdir" dist/*.whl

  # Fix shebang and add src to path
  sed -i '1s|^.*$|#!/usr/bin/python3\nimport sys\nimport os\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))|' "${pkgdir}/usr/bin/wallpicker"

  # Install desktop entry
  install -Dm644 wallpicker.desktop "${pkgdir}/usr/share/applications/wallpicker.desktop"
  sed -i 's|Exec=/home/gotar/Programowanie/wallpicker/launcher.sh|Exec=/usr/bin/wallpicker|g' "${pkgdir}/usr/share/applications/wallpicker.desktop"
  sed -i 's|Icon=/home/gotar/Programowanie/wallpicker/data/wallpaper-icon.svg|Icon=/usr/share/wallpicker/data/wallpaper-icon.svg|g' "${pkgdir}/usr/share/applications/wallpaper.desktop"

  # Install icon
  install -d "${pkgdir}/usr/share/wallpicker/data"
  install -d "${pkgdir}/usr/share/icons/hicolor/scalable/apps"
  ln -s "/usr/share/wallpicker/data/wallpaper-icon.svg" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/wallpicker.svg"

  # Install documentation
  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"

  # Install license
  install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
