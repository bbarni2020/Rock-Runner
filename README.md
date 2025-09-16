# Rock Runner

A space-themed endless runner where you navigate through asteroid fields while dodging deadly particles. Built this after getting tired of simple browser games that don't save your progress — this one actually remembers your high scores and lets you compete with other pilots.

## What It Is

You're a space pilot steering through lanes of incoming space debris. Use arrow keys or WASD to dodge particles, rack up points, and try not to die. The longer you survive, the faster things get. Simple concept, surprisingly addictive execution.

## Features That Actually Matter

- **Real progression**: Your scores save to a backend, not just localStorage
- **Multiplayer leaderboards**: See how you stack up against other players
- **User accounts**: Register once, play anywhere
- **Difficulty scaling**: Three difficulty levels (Easy/Normal/Hard)
- **Visual polish**: Particle effects, screen shake, dynamic colors that change as you play
- **Mobile support**: Touch controls for phones/tablets
- **Audio**: Background music and sound effects (can be muted)
- **AI Assistant**: A quirky captain character that gives you random space tips

## Quick Start

### For Players
1. Open `home.html` in your browser
2. Create an account or play as guest
3. Click "Launch Mission" 
4. Use arrow keys (or A/D) to move between lanes
5. Don't hit the particles
6. Press P or Space to pause

### For Developers
```bash
# Clone and enter directory
git clone <this-repo>
cd Rock-Runner

# Install Python dependencies
pip install -r requirements.txt

# Start the backend
python api.py

# Open home.html in your browser
# Backend runs on localhost:8371
```

## Controls

- **Arrow Keys** or **A/D**: Change lanes
- **P** or **Space**: Pause/Resume
- **Mobile**: Tap left/right buttons on screen

## Known Issues

- Sometimes the AI assistant says weird things (it's supposed to be quirky)
- Score validation could be stricter (but hey, don't cheat yourself)
- Mobile controls occasionally lag on older devices
- Music doesn't auto-resume on some browsers after tab switching

## Tech Stack

**Frontend**: Vanilla HTML/CSS/JavaScript (no frameworks — keeps it simple)
**Backend**: Flask + SQLite 
**Auth**: JWT tokens
**Styling**: CSS animations and transforms for all the visual effects

The whole thing is about 3000 lines of JavaScript because I got carried away with particle effects and smooth animations. No regrets.

## File Structure

```
api.py              # Flask backend with user auth and leaderboards
home.html           # Main menu / user dashboard
index.html          # The actual game
game_users.db       # SQLite database (auto-created)
requirements.txt    # Python dependencies
music.mp3           # Background music
life.mp3            # Sound effect for... reasons
icon.ico/png        # Favicons
```

## API Endpoints

The backend handles user registration, login, score tracking, and leaderboards. Check `api.py` for the full list, but main ones are:

- `POST /api/register` - Create account
- `POST /api/login` - Sign in  
- `GET /api/user/stats` - Your personal stats
- `POST /api/user/add-score` - Submit game score
- `GET /api/leaderboard/high-scores` - Global leaderboard

## Development Notes

Started as a simple lane-switching game, then added user accounts because I wanted persistent high scores. Then leaderboards because competition is fun. Then particle effects because... well, space games need particle effects.

The particle system probably uses more CPU than it should, but it looks cool so I'm keeping it. You can disable effects in settings if your machine struggles.

## AI Debugging Notes

I used GitHub Copilot to help debug some gnarly issues. If you spot weird console logs or suspiciously clean error handling, that's probably why. Honestly, AI saved me hours on the boring stuff.

## Contributing

Found a bug? Cool, open an issue. Want to add features? Even cooler, make a PR. The code's reasonably commented, though some parts got messy when I was implementing the smooth lane transitions at 2 AM.

Main areas that could use work:
- Better mobile optimization
- More sophisticated anti-cheat for scores  
- Sound effect variety
- Maybe WebGL renderer for better performance

## License

MIT - do whatever you want with it. If you make millions, buy me a coffee.

---

*Built by someone who thought "how hard could it be to make a simple browser game?" and then spent way too much time on particle physics.*