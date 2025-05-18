#!/bin/bash

echo "💡 Checking changes..."
git status

echo "➕ Staging all changes..."
git add .

echo "📝 Enter commit message:"
read msg

git commit -m "$msg"

echo "⬆️ Pushing to GitHub..."
git push origin main

echo "✅ Done. Repo updated."
