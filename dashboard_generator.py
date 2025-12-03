"""
Training Insights Dashboard
Генерация HTML dashboard с интерактивными графиками для визуализации прогресса.
"""

import datetime as dt
from typing import List, Dict, Any
from analytics import calculate_training_metrics, analyze_training_load
from utils import normalize_sport, parse_activity_date, activity_duration_hours, get_week_start


def generate_pmc_chart_data(activities: List[dict], days: int = 90) -> Dict[str, Any]:
    """
    Генерирует данные для Performance Management Chart (CTL/ATL/TSB).
    """
    today = dt.date.today()
    metrics = calculate_training_metrics(activities, today, days=days)
    
    if not metrics:
        return {"labels": [], "ctl": [], "atl": [], "tsb": []}
    
    labels = [str(m.date) for m in metrics]
    ctl_data = [round(m.ctl, 1) for m in metrics]
    atl_data = [round(m.atl, 1) for m in metrics]
    tsb_data = [round(m.tsb, 1) for m in metrics]
    
    return {
        "labels": labels,
        "ctl": ctl_data,
        "atl": atl_data,
        "tsb": tsb_data
    }


def generate_weekly_volume_data(activities: List[dict], weeks: int = 12) -> Dict[str, Any]:
    """
    Генерирует данные для графика недельного объёма.
    """
    # Группируем по неделям
    week_stats: Dict[dt.date, Dict[str, float]] = {}
    
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date:
            continue
        
        week_start = get_week_start(activity_date)
        sport = normalize_sport(activity.get("sport_type"))
        hours = activity_duration_hours(activity)
        
        if week_start not in week_stats:
            week_stats[week_start] = {
                "total": 0.0,
                "run": 0.0,
                "bike": 0.0,
                "swim": 0.0,
                "other": 0.0
            }
        
        week_stats[week_start]["total"] += hours
        week_stats[week_start][sport] = week_stats[week_start].get(sport, 0.0) + hours
    
    # Берём последние N недель
    sorted_weeks = sorted(week_stats.keys(), reverse=True)[:weeks]
    sorted_weeks.reverse()  # Сортируем от старых к новым
    
    labels = [str(week) for week in sorted_weeks]
    total_hours = [round(week_stats[week]["total"], 1) for week in sorted_weeks]
    run_hours = [round(week_stats[week].get("run", 0.0), 1) for week in sorted_weeks]
    bike_hours = [round(week_stats[week].get("bike", 0.0), 1) for week in sorted_weeks]
    swim_hours = [round(week_stats[week].get("swim", 0.0), 1) for week in sorted_weeks]
    
    return {
        "labels": labels,
        "total": total_hours,
        "run": run_hours,
        "bike": bike_hours,
        "swim": swim_hours
    }


def generate_pace_progression_data(activities: List[dict], sport: str = "run") -> Dict[str, Any]:
    """
    Генерирует данные для графика прогресса темпа на разных дистанциях.
    """
    # Целевые дистанции
    distance_ranges = {
        "5K": (4.5, 5.5),
        "10K": (9.5, 10.5),
        "HM": (20.0, 22.0)
    }
    
    pace_data = {distance: {"dates": [], "paces": []} for distance in distance_ranges.keys()}
    
    for activity in activities:
        activity_sport = normalize_sport(activity.get("sport_type"))
        if activity_sport != sport:
            continue
        
        distance = activity.get("distance")
        moving_time = activity.get("moving_time")
        activity_date = parse_activity_date(activity)
        
        if not distance or not moving_time or not activity_date:
            continue
        
        distance_km = distance / 1000
        
        # Определяем к какой дистанции относится
        for dist_name, (min_km, max_km) in distance_ranges.items():
            if min_km <= distance_km <= max_km:
                pace_per_km = moving_time / distance_km  # секунд на км
                pace_minutes = pace_per_km / 60  # минуты на км
                
                pace_data[dist_name]["dates"].append(str(activity_date))
                pace_data[dist_name]["paces"].append(round(pace_minutes, 2))
                break
    
    return pace_data


def generate_training_distribution_data(activities: List[dict], weeks: int = 12) -> Dict[str, Any]:
    """
    Генерирует данные для pie chart распределения тренировок по видам спорта
    за последние N недель.
    """
    cutoff_date = dt.date.today() - dt.timedelta(weeks=weeks)
    
    sport_hours = {
        "run": 0.0,
        "bike": 0.0,
        "swim": 0.0,
        "strength": 0.0,
        "other": 0.0
    }
    
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date or activity_date < cutoff_date:
            continue
        
        sport = normalize_sport(activity.get("sport_type"))
        hours = activity_duration_hours(activity)
        sport_hours[sport] = sport_hours.get(sport, 0.0) + hours
    
    return {
        "labels": ["Run", "Bike", "Swim", "Strength", "Other"],
        "data": [
            round(sport_hours["run"], 1),
            round(sport_hours["bike"], 1),
            round(sport_hours["swim"], 1),
            round(sport_hours["strength"], 1),
            round(sport_hours["other"], 1)
        ],
        "colors": ["#ef5350", "#42a5f5", "#66bb6a", "#ffa726", "#bdbdbd"]
    }


def generate_calendar_heatmap_data(activities: List[dict], days: int = 90) -> Dict[str, Any]:
    """
    Генерирует данные для calendar heatmap (сколько часов тренировок в каждый день).
    """
    cutoff_date = dt.date.today() - dt.timedelta(days=days)
    
    daily_hours = {}
    
    for activity in activities:
        activity_date = parse_activity_date(activity)
        if not activity_date or activity_date < cutoff_date:
            continue
        
        hours = activity_duration_hours(activity)
        
        if activity_date not in daily_hours:
            daily_hours[activity_date] = 0.0
        
        daily_hours[activity_date] += hours
    
    # Создаём полный список дней
    all_days = []
    current_date = cutoff_date
    end_date = dt.date.today()
    
    while current_date <= end_date:
        hours = daily_hours.get(current_date, 0.0)
        all_days.append({
            "date": str(current_date),
            "hours": round(hours, 1),
            "level": get_activity_level(hours)
        })
        current_date += dt.timedelta(days=1)
    
    return {"days": all_days}


def get_activity_level(hours: float) -> int:
    """Возвращает уровень активности для цвета (0-4)"""
    if hours == 0:
        return 0
    elif hours < 0.5:
        return 1
    elif hours < 1.5:
        return 2
    elif hours < 2.5:
        return 3
    else:
        return 4


def generate_dashboard_html(
    activities: List[dict],
    athlete_name: str = "Athlete"
) -> str:
    """
    Генерирует полный HTML dashboard с графиками.
    """
    # Собираем данные для графиков
    pmc_data = generate_pmc_chart_data(activities, days=90)
    volume_data = generate_weekly_volume_data(activities, weeks=12)
    pace_data = generate_pace_progression_data(activities, sport="run")
    distribution_data = generate_training_distribution_data(activities, weeks=12)
    heatmap_data = generate_calendar_heatmap_data(activities, days=90)
    
    # Текущая статистика
    training_load = analyze_training_load(activities, weeks_to_analyze=12)
    current_ctl = training_load.get('current_ctl', 0)
    current_atl = training_load.get('current_atl', 0)
    current_tsb = training_load.get('current_tsb', 0)
    form_status = training_load.get('form_interpretation', {}).get('label', 'Unknown')
    
    # Недельный объём
    total_this_week = volume_data['total'][-1] if volume_data['total'] else 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Training Dashboard - {athlete_name}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: #f5f7fa;
                color: #2d3748;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 12px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            
            .header h1 {{
                font-size: 32px;
                margin-bottom: 10px;
            }}
            
            .header p {{
                font-size: 16px;
                opacity: 0.9;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .stat-card .label {{
                font-size: 14px;
                color: #718096;
                margin-bottom: 8px;
            }}
            
            .stat-card .value {{
                font-size: 36px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 5px;
            }}
            
            .stat-card .subtitle {{
                font-size: 13px;
                color: #a0aec0;
            }}
            
            .charts-grid {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .chart-container {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .chart-container h2 {{
                font-size: 20px;
                margin-bottom: 20px;
                color: #2d3748;
            }}
            
            .chart-full-width {{
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            
            .heatmap {{
                display: grid;
                grid-template-columns: repeat(13, 1fr);
                gap: 4px;
                margin-top: 20px;
            }}
            
            .heatmap-cell {{
                aspect-ratio: 1;
                border-radius: 3px;
                position: relative;
            }}
            
            .heatmap-cell.level-0 {{ background: #ebedf0; }}
            .heatmap-cell.level-1 {{ background: #c6e48b; }}
            .heatmap-cell.level-2 {{ background: #7bc96f; }}
            .heatmap-cell.level-3 {{ background: #239a3b; }}
            .heatmap-cell.level-4 {{ background: #196127; }}
            
            .heatmap-cell:hover {{
                border: 2px solid #333;
                cursor: pointer;
            }}
            
            canvas {{
                max-height: 400px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Training Dashboard</h1>
                <p>Generated on {dt.date.today()}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">CTL (Fitness)</div>
                    <div class="value">{current_ctl}</div>
                    <div class="subtitle">Chronic Training Load</div>
                </div>
                
                <div class="stat-card">
                    <div class="label">ATL (Fatigue)</div>
                    <div class="value">{current_atl}</div>
                    <div class="subtitle">Acute Training Load</div>
                </div>
                
                <div class="stat-card">
                    <div class="label">TSB (Form)</div>
                    <div class="value">{current_tsb:+.0f}</div>
                    <div class="subtitle">{form_status}</div>
                </div>
                
                <div class="stat-card">
                    <div class="label">This Week</div>
                    <div class="value">{total_this_week:.1f}h</div>
                    <div class="subtitle">Training Volume</div>
                </div>
            </div>
            
            <div class="chart-full-width">
                <h2>Performance Management Chart (90 days)</h2>
                <canvas id="pmcChart"></canvas>
            </div>
            
            <div class="charts-grid">
                <div class="chart-container">
                    <h2>Weekly Volume Trends (12 weeks)</h2>
                    <canvas id="volumeChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h2>Training Distribution</h2>
                    <canvas id="distributionChart"></canvas>
                </div>
            </div>
            
            <div class="chart-full-width">
                <h2>Pace Progression (Run)</h2>
                <canvas id="paceChart"></canvas>
            </div>
            
            <div class="chart-full-width">
                <h2>Training Calendar Heatmap (90 days)</h2>
                <div class="heatmap" id="heatmap"></div>
            </div>
        </div>
        
        <script>
            // PMC Chart
            const pmcCtx = document.getElementById('pmcChart').getContext('2d');
            new Chart(pmcCtx, {{
                type: 'line',
                data: {{
                    labels: {pmc_data['labels']},
                    datasets: [
                        {{
                            label: 'CTL (Fitness)',
                            data: {pmc_data['ctl']},
                            borderColor: '#4299e1',
                            backgroundColor: 'rgba(66, 153, 225, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }},
                        {{
                            label: 'ATL (Fatigue)',
                            data: {pmc_data['atl']},
                            borderColor: '#f56565',
                            backgroundColor: 'rgba(245, 101, 101, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }},
                        {{
                            label: 'TSB (Form)',
                            data: {pmc_data['tsb']},
                            borderColor: '#48bb78',
                            backgroundColor: 'rgba(72, 187, 120, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'top',
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false
                        }}
                    }}
                }}
            }});
            
            // Volume Chart
            const volumeCtx = document.getElementById('volumeChart').getContext('2d');
            new Chart(volumeCtx, {{
                type: 'bar',
                data: {{
                    labels: {volume_data['labels']},
                    datasets: [
                        {{
                            label: 'Run',
                            data: {volume_data['run']},
                            backgroundColor: '#ef5350'
                        }},
                        {{
                            label: 'Bike',
                            data: {volume_data['bike']},
                            backgroundColor: '#42a5f5'
                        }},
                        {{
                            label: 'Swim',
                            data: {volume_data['swim']},
                            backgroundColor: '#66bb6a'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'top',
                        }}
                    }},
                    scales: {{
                        x: {{
                            stacked: true
                        }},
                        y: {{
                            stacked: true,
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Hours'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Distribution Chart
            const distributionCtx = document.getElementById('distributionChart').getContext('2d');
            new Chart(distributionCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {distribution_data['labels']},
                    datasets: [{{
                        data: {distribution_data['data']},
                        backgroundColor: {distribution_data['colors']}
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'right',
                        }}
                    }}
                }}
            }});
            
            // Pace Chart
            const paceCtx = document.getElementById('paceChart').getContext('2d');
            new Chart(paceCtx, {{
                type: 'line',
                data: {{
                    datasets: [
                        {{
                            label: '5K Pace',
                            data: {[{"x": date, "y": pace} for date, pace in zip(pace_data['5K']['dates'], pace_data['5K']['paces'])]},
                            borderColor: '#f56565',
                            backgroundColor: 'rgba(245, 101, 101, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        }},
                        {{
                            label: '10K Pace',
                            data: {[{"x": date, "y": pace} for date, pace in zip(pace_data['10K']['dates'], pace_data['10K']['paces'])]},
                            borderColor: '#ed8936',
                            backgroundColor: 'rgba(237, 137, 54, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        }},
                        {{
                            label: 'HM Pace',
                            data: {[{"x": date, "y": pace} for date, pace in zip(pace_data['HM']['dates'], pace_data['HM']['paces'])]},
                            borderColor: '#48bb78',
                            backgroundColor: 'rgba(72, 187, 120, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'top',
                        }}
                    }},
                    scales: {{
                        x: {{
                            type: 'time',
                            time: {{
                                unit: 'week'
                            }}
                        }},
                        y: {{
                            reverse: true,
                            title: {{
                                display: true,
                                text: 'Pace (min/km)'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Heatmap
            const heatmapData = {heatmap_data['days']};
            const heatmap = document.getElementById('heatmap');
            
            heatmapData.forEach(day => {{
                const cell = document.createElement('div');
                cell.className = `heatmap-cell level-${{day.level}}`;
                cell.title = `${{day.date}}: ${{day.hours}}h`;
                heatmap.appendChild(cell);
            }});
        </script>
    </body>
    </html>
    """
    
    return html