import PyInstaller.__main__

PyInstaller.__main__.run([
    '--onefile',
    './src/pldude.py',
    './src/build_altera.py',
    './src/build_xst.py',
    './src/build_xst7.py',
    './src/BuildConfig.py'
])