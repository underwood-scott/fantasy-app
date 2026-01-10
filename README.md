# Fantasy Playoff Scoring App

A real-time fantasy football scoring app that pulls live NFL stats from ESPN's API.

## Features
- Live scoring for QB, RB, WR, TE, FLEX, and K positions
- Point Per Reception (PPR) scoring
- Team management interface
- Real-time stat updates during games

## Quick Deploy to Render (FREE)

### Step 1: Push to GitHub
1. Create a new repository on GitHub
2. Initialize git in this folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub account and select your repository
4. Use these settings:
   - **Name**: `fantasy-app` (or whatever you prefer)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Plan**: `Free`
5. Click "Deploy Web Service"

### Step 3: Access Your App
- Render will provide a URL like: `https://fantasy-app-xyz.onrender.com`
- Share this URL with your friends!

## Local Development

Run locally:
```bash
python app.py
```

Visit:
- `http://localhost:5000` - View scores
- `http://localhost:5000/?edit=true` - Edit teams

## Usage

### Adding Teams
1. Visit the app with `?edit=true` parameter
2. Enter team name and add players by position
3. Players are auto-suggested as you type

### Viewing Scores
- Main page shows live scoring for all teams
- Scores update automatically based on live NFL games
- Points breakdown shows individual player contributions

## Scoring System

**Passing:**
- 1 point per 25 yards
- 4 points per TD
- -2 points per interception

**Rushing/Receiving:**
- 1 point per 10 yards
- 6 points per TD
- 1 point per reception (PPR)

**Kicking:**
- 3 points per field goal
- 1 point per extra point

**Defense/Special Teams:**
- Points based on points allowed (0-7 pts scale)
- 1 point per sack
- 2 points per interception/fumble recovery
- 6 points per defensive TD

## Free Tier Limitations

Render free tier includes:
- 750 hours/month (more than enough for a few weeks)
- App sleeps after 15 minutes of inactivity
- Takes ~30 seconds to wake up from sleep
- No custom domain (uses render.com subdomain)

Perfect for temporary use with friends!