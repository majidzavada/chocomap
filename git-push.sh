#!/bin/bash

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Git repository not initialized!"
    exit 1
fi

# Check if remote is set to SSH
current_remote=$(git remote get-url origin)
if [[ $current_remote == https://* ]]; then
    echo "🔄 Converting remote URL to SSH format..."
    # Extract username and repo from HTTPS URL
    repo_path=$(echo $current_remote | sed 's/https:\/\/github.com\///')
    # Set new SSH URL
    git remote set-url origin "git@github.com:$repo_path"
    echo "✅ Remote URL updated to SSH format"
fi

echo "💡 Checking changes..."
git status

echo "➕ Staging all changes..."
git add .

echo "📝 Enter commit message:"
read msg
git commit -m "$msg"

echo "⬆️ Pushing to GitHub..."
git push origin main 