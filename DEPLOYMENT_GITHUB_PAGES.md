# 🚀 Deploying Frontend to GitHub Pages

This guide will walk you through deploying the Maritime Surveillance frontend to GitHub Pages.

## 📋 Quick Checklist

- [ ] GitHub repository with frontend code
- [ ] Backend deployed on Render (or another service)
- [ ] Backend URL configured in Render environment variables
- [ ] GitHub Pages enabled in repository settings

## Prerequisites

1. **Backend Deployed**: Your backend should be deployed on Render (or another service)
   - Backend URL: `https://maritime-surveillance.onrender.com` (or your service URL)
   - CORS configured to allow your GitHub Pages URL
   - `FRONTEND_ORIGINS` includes your GitHub Pages URL

2. **GitHub Repository**: Your code should be pushed to GitHub
   - Repository: `charlotteprevost/maritime_surveillance` (or your repo)

## Option 1: GitHub Pages from `/docs` Folder (Recommended)

This is the simplest approach - GitHub Pages can serve files from a `/docs` folder in your repository.

### Step 1: Create `/docs` Folder

1. **Copy frontend files to `/docs` folder**:
   ```bash
   mkdir -p docs
   cp -r frontend/* docs/
   ```

   Or create a symlink (if supported):
   ```bash
   ln -s frontend docs
   ```

### Step 2: Configure GitHub Pages

1. **Go to Repository Settings**:
   - Navigate to: `https://github.com/charlotteprevost/maritime_surveillance/settings/pages`

2. **Configure Source**:
   - **Source**: Select `Deploy from a branch`
   - **Branch**: Select `main` (or your default branch)
   - **Folder**: Select `/docs`
   - Click **Save**

3. **Your site will be available at**:
   - `https://charlotteprevost.github.io/maritime_surveillance/`

### Step 3: Update Backend CORS Configuration

1. **Update Render Environment Variables**:
   - Go to your Render dashboard
   - Edit your service
   - Go to **Environment** tab
   - Update `FRONTEND_ORIGINS` to include your GitHub Pages URL:
     ```
     https://charlotteprevost.github.io,http://localhost:8080
     ```
   - Save changes (service will redeploy)

2. **Update `BACKEND_URL`**:
   - Ensure `BACKEND_URL` is set correctly:
     ```
     https://maritime-surveillance.onrender.com
     ```

### Step 4: Test Deployment

1. **Wait for GitHub Pages to build** (usually 1-2 minutes)
2. **Visit your site**: `https://charlotteprevost.github.io/maritime_surveillance/`
3. **Check browser console** for any errors
4. **Verify backend connection**: The frontend should fetch configs from your Render backend

## Option 2: GitHub Actions for Automatic Deployment

This approach uses GitHub Actions to automatically deploy the frontend on every push.

### Step 1: Create GitHub Actions Workflow

Create `.github/workflows/deploy-pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './frontend'

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Step 2: Enable GitHub Pages with Actions

1. **Go to Repository Settings**:
   - Navigate to: `https://github.com/charlotteprevost/maritime_surveillance/settings/pages`

2. **Configure Source**:
   - **Source**: Select `GitHub Actions`
   - Save

3. **Push the workflow file**:
   ```bash
   git add .github/workflows/deploy-pages.yml
   git commit -m "Add GitHub Actions workflow for Pages deployment"
   git push
   ```

4. **Workflow will run automatically** on next push to `main` branch

### Step 3: Update Backend CORS (Same as Option 1)

Update `FRONTEND_ORIGINS` in Render to include your GitHub Pages URL.

## Option 3: Use `gh-pages` Branch (Alternative)

This approach uses a separate branch for GitHub Pages.

### Step 1: Install gh-pages Tool

```bash
npm install --save-dev gh-pages
```

### Step 2: Add npm Script

Create or update `package.json` in project root:

```json
{
  "scripts": {
    "deploy": "gh-pages -d frontend"
  }
}
```

### Step 3: Deploy

```bash
npm run deploy
```

This will:
- Create/update `gh-pages` branch
- Copy `frontend/` files to root of `gh-pages` branch
- Push to GitHub

### Step 4: Configure GitHub Pages

1. **Go to Repository Settings** → **Pages**
2. **Source**: Select `Deploy from a branch`
3. **Branch**: Select `gh-pages` / `root`
4. **Save**

## 🔧 Backend Configuration

### Environment Variables on Render

Make sure your Render backend has these environment variables:

1. **`FRONTEND_ORIGINS`**:
   ```
   https://charlotteprevost.github.io,http://localhost:8080
   ```
   - Replace `charlotteprevost` with your GitHub username
   - Add any other frontend URLs you use

2. **`BACKEND_URL`**:
   ```
   https://maritime-surveillance.onrender.com
   ```
   - Your actual Render service URL

3. **`GFW_API_TOKEN`**:
   - Your Global Fishing Watch API token

### How Frontend Gets Backend URL

The frontend automatically fetches the backend URL from your backend's `/api/configs` endpoint:

1. Frontend loads `config.js`
2. On production (GitHub Pages), `config.backendUrl` is `null`
3. Frontend calls `/api/configs` on the backend (using the URL from `window.CONFIGS`)
4. Backend returns `backendUrl` in the response
5. Frontend uses `window.CONFIGS.backendUrl` for all API calls

**Note**: There's a chicken-and-egg problem here - the frontend needs to know the backend URL to fetch configs, but the backend URL comes from configs!

**Solution**: The frontend code in `main.js` handles this by:
- First trying `window.CONFIGS.backendUrl` (from previous load or hardcoded)
- Falling back to `config.backendUrl` (localhost for dev)

For production, you may need to hardcode the backend URL temporarily, or ensure the backend URL is set correctly.

## 🐛 Troubleshooting

### CORS Errors

**Error**: `Access-Control-Allow-Origin` errors in browser console

**Solution**:
1. Verify `FRONTEND_ORIGINS` in Render includes your GitHub Pages URL
2. Check that the URL matches exactly (including `https://`)
3. Restart Render service after updating environment variables
4. Clear browser cache

### Backend URL Not Found

**Error**: `Backend URL not configured` in browser console

**Solution**:
1. Check that `BACKEND_URL` is set in Render environment variables
2. Verify backend is accessible: `https://maritime_surveillance.onrender.com/api/configs`
3. Check browser console for network errors
4. Ensure backend service is running (not sleeping on free tier)

### 404 Errors on GitHub Pages

**Error**: Page not found or assets not loading

**Solution**:
1. Check that files are in the correct folder (`/docs` or root)
2. Verify GitHub Pages is enabled in repository settings
3. Check GitHub Pages build logs for errors
4. Ensure file paths are relative (not absolute)

### Assets Not Loading

**Error**: CSS, JS, or images not loading

**Solution**:
1. Check browser console for 404 errors
2. Verify file paths in HTML are relative (e.g., `css/style.css`, not `/css/style.css`)
3. Check that all files are committed to the repository
4. Clear browser cache

## 🔄 Updating the Frontend

### Option 1: Manual Update

1. **Make changes** to files in `frontend/` folder
2. **Copy to `/docs`** (if using Option 1):
   ```bash
   cp -r frontend/* docs/
   ```
3. **Commit and push**:
   ```bash
   git add docs/
   git commit -m "Update frontend"
   git push
   ```
4. **GitHub Pages will automatically rebuild** (may take 1-2 minutes)

### Option 2: Automatic Update (GitHub Actions)

If using Option 2 (GitHub Actions):
1. **Make changes** to files in `frontend/` folder
2. **Commit and push**:
   ```bash
   git add frontend/
   git commit -m "Update frontend"
   git push
   ```
3. **GitHub Actions will automatically deploy** (check Actions tab for status)

## 📝 GitHub Pages URL Format

Your GitHub Pages URL will be:
- **Format**: `https://<username>.github.io/<repository-name>/`
- **Example**: `https://charlotteprevost.github.io/maritime_surveillance/`

If your repository name is the same as your username, the URL is:
- `https://<username>.github.io/`

## ✅ Verification Checklist

After deployment, verify:

- [ ] GitHub Pages site is accessible
- [ ] Frontend loads without errors
- [ ] Map displays correctly
- [ ] Backend API calls work (check browser Network tab)
- [ ] CORS is configured correctly (no CORS errors in console)
- [ ] All assets (CSS, JS, images) load correctly
- [ ] Filter controls work
- [ ] EEZ selection works
- [ ] Detections display on map

## 🚀 Next Steps

1. **Custom Domain** (Optional):
   - Add custom domain in GitHub Pages settings
   - Update DNS records as instructed
   - Update `FRONTEND_ORIGINS` in Render to include custom domain

2. **Monitor Performance**:
   - Use browser DevTools to monitor load times
   - Check GitHub Pages analytics (if enabled)
   - Monitor Render backend logs

3. **Set up CI/CD**:
   - Use GitHub Actions for automated testing
   - Add deployment status badges to README

---

## Quick Reference

**GitHub Pages Settings**:
- Repository: `charlotteprevost/maritime_surveillance`
- Source: `/docs` folder or GitHub Actions
- URL: `https://charlotteprevost.github.io/maritime_surveillance/`

**Backend Configuration**:
- Service URL: `https://maritime_surveillance.onrender.com`
- `FRONTEND_ORIGINS`: `https://charlotteprevost.github.io,http://localhost:8080`
- `BACKEND_URL`: `https://maritime_surveillance.onrender.com`

---

Need help? Check GitHub Pages documentation: [docs.github.com/pages](https://docs.github.com/pages)
