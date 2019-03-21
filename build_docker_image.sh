#!/usr/bin/env bash
echo "Cloning SPA repo"
git clone https://github.com/ANIME-AnimeCoin/react_ui_spa.git
cd react_ui_spa
echo "Instaling NPM modules"
npm i

# will create react_ui_spa/dist/*
npm run build

cd ..
echo "Starting Docker build"
docker build .

echo "Clean up"
rm -rf react_ui_spa

echo "Done!"
