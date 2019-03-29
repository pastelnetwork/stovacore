#!/usr/bin/env bash
echo "Cloning SPA repo"
git clone https://github.com/ANIME-AnimeCoin/PastelWallet.git
cd PastelWallet
echo "Instaling NPM modules"
npm i

# will create react_ui_spa/dist/*
npm run build

cd ..
echo "Starting Docker build"
docker build .

echo "Clean up"
rm -rf PastelWallet

echo "Done!"
