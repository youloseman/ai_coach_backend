"""
Running-specific training module.
"""

RUNNING_MODULE = """
# RUNNING-SPECIFIC TRAINING GUIDE

## TRAINING ZONES FOR RUNNING

### Method 1: Heart Rate Based (Karvonen Formula)
Max HR = 220 - age (or use tested max HR)
HR Reserve = Max HR - Resting HR

Zone 1 (Recovery): Resting HR + (0.50-0.60 × HR Reserve)
Zone 2 (Endurance): Resting HR + (0.60-0.70 × HR Reserve)
Zone 3 (Tempo): Resting HR + (0.70-0.80 × HR Reserve)
Zone 4 (Threshold): Resting HR + (0.80-0.90 × HR Reserve)
Zone 5 (VO2max): Resting HR + (0.90-1.00 × HR Reserve)

**Example:** Age 35, Max HR 185, Resting HR 55
- HR Reserve = 185 - 55 = 130
- Zone 2 = 55 + (0.60 × 130) = 133 bpm to 55 + (0.70 × 130) = 146 bpm

### Method 2: Pace Based (Jack Daniels' VDOT)

**Step 1: Determine VDOT from recent race**
Use VDOT calculator or recent race time.

**Step 2: Calculate pace zones from VDOT**
Easy Pace (Zone 1-2): VDOT + 60-90 sec per km
Marathon Pace (Zone 3): VDOT - 15 to +15 sec per km
Threshold Pace (Zone 4): VDOT - 30 sec per km
Interval Pace (Zone 5): VDOT - 50 sec per km
Repetition Pace (Zone 5+): VDOT - 60+ sec per km

**Example:** VDOT 45 → 10K pace = 4:30/km
- Easy: 5:30-6:00/km
- Marathon: 4:45-5:00/km
- Threshold: 4:15/km
- Interval: 3:55/km
- Reps: <3:45/km

### Method 3: Perceived Exertion (RPE)
- Zone 1-2: RPE 2-4 / Can sing
- Zone 3: RPE 5-6 / Can talk in phrases
- Zone 4: RPE 7-8 / Few words only
- Zone 5: RPE 9-10 / Cannot talk

## KEY RUNNING WORKOUTS

### 1. LONG RUN (Weekly Foundation)
**Purpose:** Build aerobic base, mental toughness, fat adaptation

**Format:**
- Duration: 90-180 minutes depending on goal distance
- Pace: Zone 2 (comfortable, conversational)
- Cadence: 170-180 steps per minute
- Progression: Increase by 10-15 min per week, every 4th week reduce

### 2. TEMPO RUN (Threshold Development)
**Purpose:** Raise lactate threshold, improve race pace endurance

**Format:**
- Warmup: 10-15 min easy
- Main set: 20-40 min at threshold pace (Zone 4)
- Cooldown: 10 min easy
- Frequency: 1x per week

### 3. INTERVAL TRAINING (VO2max)
**Purpose:** Increase maximum oxygen uptake, improve speed

**Classic workouts:**
- 5x1000m at Zone 5 with 400m jog recovery
- 8x800m at Zone 5+ with 400m jog recovery
- Fartlek: 3 min hard, 2 min easy, repeat 6 times

### 4. EASY RUNS (Recovery & Volume)
**Purpose:** Active recovery, build aerobic base, add volume safely

**Format:**
- Duration: 30-60 minutes
- Pace: Zone 1-2 (very comfortable)
- Frequency: 3-5x per week
- Rule: If you can't hold conversation, you're too fast - SLOW DOWN

### 5. HILL TRAINING
**Purpose:** Build strength, power, running economy

**Format:**
- Warmup: 15 min easy
- Find hill: 6-10% grade, 200-400m long
- Repeats: 6-12 × 60-90 seconds hard uphill
- Recovery: Jog down easy
- Cooldown: 10 min easy

### 6. STRIDES (Technique & Speed)
**Purpose:** Improve running form, neuromuscular coordination

**Format:**
- 4-8 × 100m accelerations
- Build to 90% of max speed over 20m
- Hold for 60m, decelerate last 20m
- Full recovery between (1-2 min walk back)
- When: End of easy runs, 2-3x per week

## SAMPLE WEEK STRUCTURE

### Beginner Runner (5K Goal)
- Monday: Rest
- Tuesday: Easy 30 min + 4 strides
- Wednesday: Tempo 15 min (Zone 3-4)
- Thursday: Easy 30 min
- Friday: Rest
- Saturday: Long 60 min (Zone 2)
- Sunday: Easy 30 min or cross-training

### Intermediate Runner (Half Marathon)
- Monday: Rest or easy 30 min
- Tuesday: Intervals: 5x1000m at threshold + 400m recovery
- Wednesday: Easy 45 min
- Thursday: Tempo 30 min at marathon pace
- Friday: Easy 30 min + 6 strides
- Saturday: Long 100-120 min
- Sunday: Easy 45-60 min

### Advanced Runner (Marathon)
- Monday: Rest or 30 min easy
- Tuesday: Intervals: 8x800m at 5K pace
- Wednesday: Easy 60 min
- Thursday: Tempo: 10 min easy + 40 min threshold + 10 min easy
- Friday: Easy 45 min + strides
- Saturday: Long 150-180 min with last 30 min at marathon pace
- Sunday: Easy 60-90 min

## RUNNING-SPECIFIC STRENGTH TRAINING

**2x per week, 30 minutes per session**

**Essential exercises:**
1. Single-leg squats (3×10 each leg)
2. Deadlifts (3×12)
3. Calf raises (3×20)
4. Planks (3×60 seconds)
5. Side planks (3×45 seconds each side)
6. Glute bridges (3×15)
7. Leg swings (2×20 each direction)

**When:** After easy runs or separate day, NOT before hard workouts

## RUNNING FORM CUES

**Optimal running form:**
- **Cadence:** 170-180 steps per minute (reduce injury risk)
- **Foot strike:** Midfoot under center of mass (not heel strike out front)
- **Posture:** Tall, slight forward lean from ankles
- **Arms:** 90-degree bend, swing forward/back (not across body)
- **Shoulders:** Relaxed, not hunched
- **Head:** Look ahead 10-20m, not down at feet
- **Breathing:** Rhythmic, belly breathing

**Common mistakes:**
- Overstriding (landing heel-first way out in front)
- Slouching/hunching shoulders
- Crossing arms across body
- Bouncing too much (vertical oscillation)
- Too slow cadence (<160 spm)

## RACE-SPECIFIC TRAINING

### 5K Race Strategy
- 90% effort first 1K
- Settle into threshold pace 1-4K
- All-out last 500m
- Practice race pace in training: 5x1K at goal pace

### 10K Race Strategy
- Start controlled first 2K
- Find rhythm 2-8K at threshold
- Push final 2K
- Practice: 3x3K at goal pace

### Half Marathon Strategy
- First 5K: 10 seconds per km slower than goal pace
- Middle 10K: At goal pace
- Last 5K: If feeling good, push 5-10 sec/km faster
- Practice: Long runs with last 30-45 min at goal pace

### Marathon Strategy
- First 10K: 15-20 sec/km slower than goal pace (feels TOO easy - good!)
- 10-30K: Settle at goal pace
- 30-40K: Hold pace (this is where it gets hard)
- Last 2K: Empty the tank
- Practice: Multiple 25-30K runs with last 10K at goal pace

## TAPER STRATEGY FOR RUNNING

**3 weeks out:**
- Reduce volume 20%
- Keep intensity with shorter intervals

**2 weeks out:**
- Reduce volume 40%
- Include some race pace work

**Race week:**
- Reduce volume 60-70%
- Monday/Tuesday: Easy + a few strides
- Wednesday: 20 min with 3x3min at race pace
- Thursday/Friday: 20-30 min easy
- Saturday: Rest or 15 min shakeout + strides
- Sunday: RACE!

## RED FLAGS (When to Rest/Reduce)

1. **Elevated resting heart rate** (5+ bpm above normal) → Easy day or rest
2. **Persistent fatigue** (feels tired on easy runs) → Take 2-3 days very easy
3. **Pain that worsens during run** → Stop immediately, assess
4. **Insomnia/poor sleep quality** → Reduce intensity until sleep normalizes
5. **Loss of motivation/grumpy** → Classic overtraining sign, take rest

## INJURY PREVENTION CHECKLIST

- [ ] Increase weekly volume by <10% per week
- [ ] Include 1 full rest day per week
- [ ] Do dynamic warmup before hard workouts
- [ ] Strength train 2x per week
- [ ] Replace shoes every 500-800 km
- [ ] Listen to pain signals
- [ ] Include easy runs (Zone 1-2) majority of the time
- [ ] Sleep 7-9 hours per night
- [ ] Stay hydrated and eat enough
- [ ] Don't race every weekend

---

END OF RUNNING MODULE
"""

