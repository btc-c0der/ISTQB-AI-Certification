#!/bin/bash
# Script to deploy the ISTQB AI Testing Portal to HuggingFace Spaces

echo "===== ISTQB AI Testing Portal - HuggingFace Deployment Script ====="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git first."
    exit 1
fi

# Check if huggingface_hub is installed
if ! python -c "import huggingface_hub" &> /dev/null; then
    echo "Installing huggingface_hub..."
    pip install huggingface_hub
fi

echo "Step 1: Preparing repository for deployment..."

# Check if the .env file exists and warn if it does
if [ -f .env ]; then
    echo "Warning: .env file detected. Make sure it doesn't contain sensitive information."
    echo "Your .env file should NOT be committed to HuggingFace Spaces."
    read -p "Continue deployment? (y/n): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Deployment canceled."
        exit 0
    fi
fi

# Create or update app.py in the root directory if it's in app/app.py
if [ -f app/app.py ] && [ ! -f app.py ]; then
    echo "Copying app/app.py to root directory for HuggingFace Spaces compatibility..."
    cp app/app.py app.py
fi

# Create data directory if it doesn't exist
if [ ! -d data ]; then
    echo "Creating data directory..."
    mkdir -p data
fi

# Create llm_evals directory if it doesn't exist
if [ ! -d data/llm_evals ]; then
    echo "Creating data/llm_evals directory..."
    mkdir -p data/llm_evals
    # Create empty evaluations.json file
    echo '{"evaluations": []}' > data/llm_evals/evaluations.json
fi

echo "Step 2: Login to HuggingFace Hub..."
echo "You'll need to authenticate to HuggingFace to push your code."
echo "Opening browser for HuggingFace login..."

# Login to HF Hub
python -c "from huggingface_hub import login; login()"

echo "Step 3: Cloning HuggingFace Space repository..."
# Clone the Space if it exists, otherwise create it
SPACE_NAME="fartec0/AI-testing-portal"
TMP_DIR="tmp_hf_space"

if [ -d "$TMP_DIR" ]; then
    echo "Removing existing temporary directory..."
    rm -rf "$TMP_DIR"
fi

# Try to clone the existing space, create if it doesn't exist
if ! git clone "https://huggingface.co/spaces/$SPACE_NAME" "$TMP_DIR" 2>/dev/null; then
    echo "Space doesn't exist yet. Creating new Space..."
    python -c "from huggingface_hub import create_repo; create_repo('$SPACE_NAME', repo_type='space', space_sdk='gradio')"
    git clone "https://huggingface.co/spaces/$SPACE_NAME" "$TMP_DIR"
fi

echo "Step 4: Copying project files to Space repository..."
# Copy all important files to the temporary directory
for item in app app.py data db hf_integration.py models requirements.txt tests utils README-HF.md .gitignore; do
    if [ -e "$item" ]; then
        echo "Copying $item..."
        cp -r "$item" "$TMP_DIR/"
    fi
done

# Rename README-HF.md to README.md in the Space
if [ -f "$TMP_DIR/README-HF.md" ]; then
    echo "Using README-HF.md as README.md..."
    mv "$TMP_DIR/README-HF.md" "$TMP_DIR/README.md"
fi

# Go to the Space directory
cd "$TMP_DIR"

echo "Step 5: Committing and pushing to HuggingFace Spaces..."
git add .
git config --local user.email "user@example.com"
git config --local user.name "ISTQB AI Testing Portal"
git commit -m "Deploy ISTQB AI Testing Portal"

# Push to HuggingFace
echo "Pushing to HuggingFace Spaces..."
git push

echo "Step 6: Cleaning up..."
cd ..
rm -rf "$TMP_DIR"

echo "===== Deployment Complete! ====="
echo "Your ISTQB AI Testing Portal should now be available at:"
echo "https://huggingface.co/spaces/$SPACE_NAME"
echo ""
echo "Note: It may take a few minutes for the Space to build and deploy."
echo "You can check the build status on the Space's page."
echo ""
echo "To check for any build issues, visit the 'Settings' tab in your Space and look at the 'Logs' section."
