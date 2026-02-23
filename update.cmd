git submodule update --remote --merge
git add .
git commit -m "update submodule to latest"
git push


git fetch upstream
git checkout main
git merge upstream/main
git status
git add .
git commit -m "resolve conflicts with upstream"
git push origin main


git checkout --theirs i18n/en_US.json
git add i18n/en_US.json
git commit -m "resolve conflict: accept upstream's en_US.json modification"
git push origin main
git status