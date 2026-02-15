# Release Process

1. Update version in version.py
2. Commit changes
3. Create tag:

   git tag vX.X.X
   git push origin vX.X.X

4. Build exe:

   build_exe.bat

5. Compile installer with Inno Setup
6. Upload installer to GitHub Releases
