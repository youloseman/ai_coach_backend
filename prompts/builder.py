"""
Prompt builder that assembles modular prompts.
"""

from datetime import datetime
from .base_prompt import BASE_SYSTEM_PROMPT
from .sport_modules import (
    TRIATHLON_MODULE,
    RUNNING_MODULE,
    SWIMMING_MODULE,
)


def build_coach_prompt(
    sport_type: str,
    athlete_profile: dict,
    goal: dict,
    recent_activities: list = None
) -> str:
    """
    Assemble complete AI prompt from modules
    
    Args:
        sport_type: 'triathlon', 'run', 'swim', 'cycling', etc.
        athlete_profile: User profile data (age, gender, experience, zones)
        goal: Goal data (race type, date, target time)
        recent_activities: Last 12 weeks of training (optional)
    
    Returns:
        Complete prompt string ready for GPT
    """
    
    # Start with base prompt (always included)
    prompt = BASE_SYSTEM_PROMPT
    
    # Add sport-specific module
    sport_modules = {
        'triathlon': TRIATHLON_MODULE,
        'run': RUNNING_MODULE,
        'running': RUNNING_MODULE,
        'swim': SWIMMING_MODULE,
        'swimming': SWIMMING_MODULE,
    }
    
    sport_module = sport_modules.get(sport_type.lower(), RUNNING_MODULE)
    prompt += "\n\n" + sport_module
    
    # Add athlete context
    prompt += build_athlete_context(athlete_profile)
    
    # Add goal context
    prompt += build_goal_context(goal)
    
    # Add training history if available
    if recent_activities:
        prompt += build_training_history(recent_activities)
    
    # Add zone calculations if available
    if athlete_profile.get('training_zones'):
        prompt += build_zones_section(athlete_profile['training_zones'])
    
    return prompt


def build_athlete_context(profile: dict) -> str:
    """Build athlete profile section"""
    return f"""

# ATHLETE PROFILE

**Demographics:**
- Age: {profile.get('age', 'Not provided')}
- Gender: {profile.get('gender', 'Not provided')}
- Experience: {profile.get('years_of_experience', 0)} years

**Current Fitness:**
- Recent weekly hours: {profile.get('avg_hours_per_week', 'Unknown')}
- Current weekly streak: {profile.get('current_streak', 'Unknown')} weeks
- Longest streak: {profile.get('longest_streak', 'Unknown')} weeks

**Training Availability:**
- Available hours per week: {profile.get('available_hours_per_week', 8)}
- Preferred training days: {', '.join(profile.get('preferred_training_days', ['Not specified']))}

**Limitations/Notes:**
{profile.get('notes', 'None provided')}

---
"""


def build_goal_context(goal: dict) -> str:
    """Build goal section"""
    weeks_to_race = calculate_weeks_until(goal.get('race_date', ''))
    
    return f"""

# GOAL INFORMATION

**Event Details:**
- Type: {goal.get('goal_type', 'Not specified')}
- Race date: {goal.get('race_date', 'Not specified')}
- Weeks until race: {weeks_to_race}
- Race name: {goal.get('race_name', 'Not specified')}

**Target:**
- Goal time: {goal.get('target_time', 'Finish strong')}
- Priority: {'A-race (primary goal)' if goal.get('is_primary') else 'B-race (training race)'}

---
"""


def build_training_history(activities: list) -> str:
    """Build training history section"""
    # Analyze activities to show recent load
    total_hours = sum(a.get('duration_hours', 0) for a in activities if isinstance(a, dict))
    avg_per_week = total_hours / 12 if activities else 0
    
    return f"""

# RECENT TRAINING HISTORY (Last 12 weeks)

**Volume:**
- Total hours: {total_hours:.1f} hours
- Average per week: {avg_per_week:.1f} hours

**Distribution:** [Automatically calculated from Strava]

**Recent trends:** [AI will analyze activities list]

---
"""


def build_zones_section(zones: dict) -> str:
    """Build training zones section"""
    return f"""

# ATHLETE'S TRAINING ZONES

**Important:** Use these specific zones when prescribing workouts!

{format_zones_for_prompt(zones)}

---
"""


def calculate_weeks_until(race_date: str) -> int:
    """Calculate weeks from now to race"""
    if not race_date:
        return 0
    
    try:
        race = datetime.strptime(race_date, '%Y-%m-%d')
        now = datetime.now()
        delta = race - now
        return max(1, delta.days // 7)
    except (ValueError, TypeError):
        return 0


def format_zones_for_prompt(zones: dict) -> str:
    """Format zones nicely for GPT"""
    if not zones:
        return "No zones provided. Calculate zones using sport-specific formulas."
    
    output = ""
    
    if isinstance(zones, dict):
        if 'run' in zones and zones['run']:
            output += "**Running Zones:**\n"
            run_zones = zones['run']
            if isinstance(run_zones, dict):
                for zone_name, zone_data in run_zones.items():
                    output += f"- {zone_name}: {zone_data}\n"
            else:
                output += f"- {run_zones}\n"
            output += "\n"
        
        if 'bike' in zones and zones['bike']:
            output += "**Cycling Zones:**\n"
            bike_zones = zones['bike']
            if isinstance(bike_zones, dict):
                for zone_name, zone_data in bike_zones.items():
                    output += f"- {zone_name}: {zone_data}\n"
            else:
                output += f"- {bike_zones}\n"
            output += "\n"
        
        if 'swim' in zones and zones['swim']:
            output += "**Swimming Zones:**\n"
            swim_zones = zones['swim']
            if isinstance(swim_zones, dict):
                for zone_name, zone_data in swim_zones.items():
                    output += f"- {zone_name}: {zone_data}\n"
            else:
                output += f"- {swim_zones}\n"
            output += "\n"
    
    return output if output else "No zones provided. Calculate zones using sport-specific formulas."

