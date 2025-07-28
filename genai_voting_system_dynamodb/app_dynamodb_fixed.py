import json
import boto3
import os
import logging
from decimal import Decimal
from datetime import datetime
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')

# Table references
TEAMS_TABLE = os.environ.get('TEAMS_TABLE')
JUDGES_TABLE = os.environ.get('JUDGES_TABLE')
VOTES_TABLE = os.environ.get('VOTES_TABLE')
CRITERIA_TABLE = os.environ.get('CRITERIA_TABLE')
SETTINGS_TABLE = os.environ.get('SETTINGS_TABLE')

teams_table = dynamodb.Table(TEAMS_TABLE)
judges_table = dynamodb.Table(JUDGES_TABLE)
votes_table = dynamodb.Table(VOTES_TABLE)
criteria_table = dynamodb.Table(CRITERIA_TABLE)
settings_table = dynamodb.Table(SETTINGS_TABLE)

def get_security_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Max-Age': '86400'
    }

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def initialize_database():
    """Initialize DynamoDB tables with CORRECT criteria weights"""
    try:
        # Initialize criteria with CORRECT weights from documentation
        criteria_response = criteria_table.scan(Select='COUNT')
        if criteria_response['Count'] == 0:
            criteria_data = [
                {"id": "1", "name": "Problem Understanding", "weight": Decimal('15'), "max_score": 1, "description": "Did the team demonstrate deep understanding of the customer's problem?"},
                {"id": "2", "name": "Success Criteria Definition", "weight": Decimal('15'), "max_score": 1, "description": "Did the team determine success criteria collaboratively with the customer?"},
                {"id": "3", "name": "Demo Relevance", "weight": Decimal('15'), "max_score": 1, "description": "Did the team present a demo that directly addresses the customer problem?"},
                {"id": "4", "name": "Service Correlation", "weight": Decimal('15'), "max_score": 1, "description": "Did the team effectively correlate the demo with AWS services for the PoC?"},
                {"id": "5", "name": "GenAI Services Usage", "weight": Decimal('15'), "max_score": 1, "description": "Did the team leverage AWS GenAI services appropriately?"},
                {"id": "6", "name": "Team Collaboration", "weight": Decimal('10'), "max_score": 1, "description": "Did the team demonstrate effective collaboration during the presentation?"},
                {"id": "7", "name": "Notes of Unanswered Questions", "weight": Decimal('15'), "max_score": 1, "description": "Did the team take notes of the unanswered questions to address later?"}
            ]
            
            for criteria in criteria_data:
                criteria_table.put_item(Item=criteria)
            logger.info("Added criteria with correct weights")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def lambda_handler(event, context):
    try:
        # Initialize database on first call
        initialize_database()
        
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_security_headers(),
                'body': ''
            }
        
        path = event.get('path', '').rstrip('/')
        method = event.get('httpMethod', 'GET')
        
        logger.info(f"Request: {method} {path}")
        
        # Handle main page
        if path == '' or path == '/':
            return serve_main_page()
        
        # Remove /api prefix if present
        if path.startswith('/api'):
            path = path[4:]
        
        # API Routes
        if method == 'GET' and path == '/teams':
            response = teams_table.scan()
            teams = response['Items']
            for team in teams:
                team['competition_name'] = 'Ignite Innovative GenAI Training'
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps(teams, default=decimal_default)
            }
        
        elif method == 'POST' and path == '/teams':
            body = json.loads(event.get('body', '{}'))
            name = body.get('name', '').strip()
            description = body.get('description', '').strip()
            
            if not name:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Team name is required'})
                }
            
            team_id = str(uuid.uuid4())
            team = {
                'id': team_id,
                'name': name,
                'description': description,
                'competition_id': '1',
                'created_at': datetime.now().isoformat()
            }
            
            teams_table.put_item(Item=team)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({'id': team_id, 'name': name, 'description': description, 'message': 'Team added successfully'})
            }
        
        elif method == 'GET' and path == '/judges':
            response = judges_table.scan()
            judges = response['Items']
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps(judges, default=decimal_default)
            }
        
        elif method == 'POST' and path == '/judges':
            body = json.loads(event.get('body', '{}'))
            name = body.get('name', '').strip()
            email = body.get('email', '').strip()
            role = body.get('role', '').strip()
            
            if not name or not email:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Name and email are required'})
                }
            
            judge_id = str(uuid.uuid4())
            judge = {
                'id': judge_id,
                'name': name,
                'email': email,
                'role': role,
                'created_at': datetime.now().isoformat()
            }
            
            judges_table.put_item(Item=judge)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({'id': judge_id, 'name': name, 'email': email, 'role': role, 'message': 'Judge added successfully'})
            }
        
        elif method == 'GET' and path == '/criteria':
            response = criteria_table.scan()
            criteria = response['Items']
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps(criteria, default=decimal_default)
            }
        
        elif method == 'POST' and path == '/vote':
            body = json.loads(event.get('body', '{}'))
            judge_id = str(body.get('judge_id', ''))
            team_id = str(body.get('team_id', ''))
            criteria_id = str(body.get('criteria_id', ''))
            score = body.get('score', 0)
            comments = body.get('comments', '')
            
            if not all([judge_id, team_id, criteria_id]):
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Judge ID, Team ID, and Criteria ID are required'})
                }
            
            vote_id = str(uuid.uuid4())
            vote = {
                'id': vote_id,
                'judge_id': judge_id,
                'team_id': team_id,
                'criteria_id': criteria_id,
                'score': Decimal(str(score)),
                'comments': comments,
                'created_at': datetime.now().isoformat()
            }
            
            votes_table.put_item(Item=vote)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({
                    'message': 'Vote submitted successfully',
                    'judge_id': judge_id,
                    'team_id': team_id,
                    'criteria_id': criteria_id,
                    'score': score
                })
            }
        
        elif method == 'GET' and path == '/votes':
            response = votes_table.scan()
            votes = response['Items']
            
            # Enrich votes with team and judge names
            teams_response = teams_table.scan()
            judges_response = judges_table.scan()
            criteria_response = criteria_table.scan()
            
            teams_dict = {team['id']: team for team in teams_response['Items']}
            judges_dict = {judge['id']: judge for judge in judges_response['Items']}
            criteria_dict = {criteria['id']: criteria for criteria in criteria_response['Items']}
            
            for vote in votes:
                team = teams_dict.get(vote['team_id'], {})
                judge = judges_dict.get(vote['judge_id'], {})
                criteria = criteria_dict.get(vote['criteria_id'], {})
                
                vote['team_name'] = team.get('name', 'Unknown Team')
                vote['judge_name'] = judge.get('name', 'Unknown Judge')
                vote['criteria_name'] = criteria.get('name', 'Unknown Criteria')
                vote['max_score'] = criteria.get('max_score', 1)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps(votes, default=decimal_default)
            }
        
        elif method == 'GET' and path == '/leaderboard':
            # CORRECTED SCORING FORMULA: (Total Yes / Total Possible Yes) × 100
            teams_response = teams_table.scan()
            votes_response = votes_table.scan()
            judges_response = judges_table.scan()
            
            teams = teams_response['Items']
            votes = votes_response['Items']
            judges = judges_response['Items']
            
            # Calculate scores for each team using CORRECT formula
            team_scores = {}
            for team in teams:
                team_id = team['id']
                team_votes = [v for v in votes if v['team_id'] == team_id]
                
                # Count total "Yes" votes for this team
                total_yes = sum(1 for vote in team_votes if float(vote['score']) == 1)
                
                # Count unique judges who voted for this team
                judges_who_voted = set(v['judge_id'] for v in team_votes)
                judge_count = len(judges_who_voted)
                
                # Total possible "Yes" = 7 criteria × number of judges who voted
                total_possible_yes = 7 * judge_count if judge_count > 0 else 0
                
                # Calculate percentage: (Total Yes / Total Possible Yes) × 100
                final_percentage = (total_yes / total_possible_yes * 100) if total_possible_yes > 0 else 0
                
                team_scores[team_id] = {
                    'id': team['id'],
                    'team_name': team['name'],
                    'description': team.get('description', ''),
                    'total_yes_votes': total_yes,
                    'total_possible_yes': total_possible_yes,
                    'final_percentage': final_percentage,
                    'vote_count': len(team_votes),
                    'judge_count': judge_count
                }
            
            # Sort by final percentage descending (correct ranking)
            leaderboard = sorted(team_scores.values(), 
                               key=lambda x: x['final_percentage'], 
                               reverse=True)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps(leaderboard, default=decimal_default)
            }
        
        elif method == 'POST' and path == '/clear-sample-data':
            # Clear all data
            deleted_teams = 0
            deleted_judges = 0
            deleted_votes = 0
            
            # Clear votes
            votes_response = votes_table.scan()
            for vote in votes_response['Items']:
                votes_table.delete_item(Key={'id': vote['id']})
                deleted_votes += 1
            
            # Clear teams
            teams_response = teams_table.scan()
            for team in teams_response['Items']:
                teams_table.delete_item(Key={'id': team['id']})
                deleted_teams += 1
            
            # Clear judges
            judges_response = judges_table.scan()
            for judge in judges_response['Items']:
                judges_table.delete_item(Key={'id': judge['id']})
                deleted_judges += 1
            
            # Clear criteria to force re-initialization with correct weights
            criteria_response = criteria_table.scan()
            for criteria in criteria_response['Items']:
                criteria_table.delete_item(Key={'id': criteria['id']})
            
            # Set clear flags
            settings_table.put_item(Item={'key': 'sample_data_cleared', 'value': 'true'})
            settings_table.put_item(Item={'key': 'data_cleared_at', 'value': datetime.now().isoformat()})
            settings_table.put_item(Item={'key': 'user_managed', 'value': 'true'})
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({
                    'message': 'All data cleared successfully - criteria will be re-initialized with correct weights',
                    'deleted_teams': deleted_teams,
                    'deleted_judges': deleted_judges,
                    'deleted_votes': deleted_votes,
                    'reset_counters': True
                })
            }
        
        elif method == 'GET' and path == '/debug-db':
            # Get all data
            teams_response = teams_table.scan()
            judges_response = judges_table.scan()
            votes_response = votes_table.scan()
            criteria_response = criteria_table.scan()
            settings_response = settings_table.scan()
            
            teams = [{'id': t['id'], 'name': t['name']} for t in teams_response['Items']]
            judges = [{'id': j['id'], 'name': j['name']} for j in judges_response['Items']]
            votes = [{'id': v['id'], 'judge_id': v['judge_id'], 'team_id': v['team_id'], 'criteria_id': v['criteria_id'], 'score': float(v['score'])} for v in votes_response['Items']]
            criteria = [{'id': c['id'], 'name': c['name'], 'weight': float(c['weight'])} for c in criteria_response['Items']]
            settings = [{'key': s['key'], 'value': s['value']} for s in settings_response['Items']]
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({
                    'database_state': {
                        'teams': teams,
                        'judges': judges,
                        'votes': votes,
                        'criteria': criteria,
                        'settings': settings
                    },
                    'counts': {
                        'teams': len(teams),
                        'judges': len(judges),
                        'votes': len(votes),
                        'criteria': len(criteria)
                    }
                }, indent=2)
            }
        
        # 404 for unknown routes
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json', **get_security_headers()},
            'body': json.dumps({'error': f'Not found: {method} {path}'})
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', **get_security_headers()},
            'body': json.dumps({'error': 'Internal server error'})
        }

def serve_main_page():
    """Serve the complete voting application with documentation and corrected scoring"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            **get_security_headers()
        },
        'body': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ignite Innovative GenAI Training - Voting System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 3rem 0; 
        }
        .card { 
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
            border: none; 
            margin-bottom: 1.5rem; 
        }
        .nav-tabs .nav-link.active { 
            background-color: #667eea; 
            border-color: #667eea; 
            color: white; 
        }
        .btn-primary { 
            background-color: #667eea; 
            border-color: #667eea; 
        }
        .btn-primary:hover { 
            background-color: #5a6fd8; 
            border-color: #5a6fd8; 
        }
        .leaderboard-item { 
            transition: all 0.3s ease; 
        }
        .leaderboard-item:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); 
        }
        .score-badge { 
            font-size: 1.2rem; 
            padding: 0.5rem 1rem; 
        }
        .documentation { 
            font-size: 0.9rem; 
            line-height: 1.4; 
        }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <div class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-8">
                    <h1 class="display-4 fw-bold mb-3">
                        <i class="fas fa-trophy me-3"></i>
                        Ignite Innovative GenAI Training
                    </h1>
                    <p class="lead mb-4">Competition Voting System - Corrected Scoring Formula</p>
                    <div class="d-flex gap-3">
                        <span class="badge bg-success fs-6">
                            <i class="fas fa-database me-1"></i>
                            DynamoDB Persistent
                        </span>
                        <span class="badge bg-info fs-6">
                            <i class="fas fa-calculator me-1"></i>
                            Correct Formula: (Yes/Total) × 100
                        </span>
                    </div>
                </div>
                <div class="col-lg-4 text-center">
                    <i class="fas fa-award fa-8x opacity-75"></i>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="container mt-4">
        <!-- Navigation Tabs -->
        <ul class="nav nav-tabs mb-4" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="voting-tab" data-bs-toggle="tab" data-bs-target="#voting" type="button" role="tab">
                    <i class="fas fa-vote-yea me-2"></i>Voting
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="leaderboard-tab" data-bs-toggle="tab" data-bs-target="#leaderboard" type="button" role="tab">
                    <i class="fas fa-trophy me-2"></i>Leaderboard
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="teams-tab" data-bs-toggle="tab" data-bs-target="#teams" type="button" role="tab">
                    <i class="fas fa-users me-2"></i>Teams
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="judges-tab" data-bs-toggle="tab" data-bs-target="#judges" type="button" role="tab">
                    <i class="fas fa-user-tie me-2"></i>Judges
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="documentation-tab" data-bs-toggle="tab" data-bs-target="#documentation" type="button" role="tab">
                    <i class="fas fa-book me-2"></i>Documentation
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="admin-tab" data-bs-toggle="tab" data-bs-target="#admin" type="button" role="tab">
                    <i class="fas fa-cog me-2"></i>Admin
                </button>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content" id="mainTabContent">
            <!-- Voting Tab -->
            <div class="tab-pane fade show active" id="voting" role="tabpanel">
                <div class="row">
                    <div class="col-lg-8">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h5 class="mb-0">
                                    <i class="fas fa-vote-yea me-2"></i>
                                    Cast Your Vote
                                </h5>
                            </div>
                            <div class="card-body">
                                <div id="voting-interface">
                                    <div class="text-center">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                        <p class="mt-2">Loading voting interface...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-4">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas fa-info-circle me-2"></i>
                                    Voting Instructions
                                </h6>
                            </div>
                            <div class="card-body">
                                <ol class="small">
                                    <li>Select a judge from the dropdown</li>
                                    <li>Choose a team to evaluate</li>
                                    <li>Vote Yes/No for each criterion</li>
                                    <li>Add optional comments</li>
                                    <li>Submit your votes</li>
                                </ol>
                                <div class="alert alert-info small">
                                    <i class="fas fa-calculator me-1"></i>
                                    <strong>Scoring:</strong> Final Score = (Total Yes / Total Possible Yes) × 100
                                </div>
                                <div class="alert alert-warning small">
                                    <i class="fas fa-exclamation-triangle me-1"></i>
                                    <strong>Note:</strong> All criteria are weighted equally except Team Collaboration (10%).
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Leaderboard Tab -->
            <div class="tab-pane fade" id="leaderboard" role="tabpanel">
                <div class="card">
                    <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-trophy me-2"></i>
                            Competition Leaderboard - Corrected Scoring
                        </h5>
                        <button class="btn btn-light btn-sm" onclick="loadLeaderboard()">
                            <i class="fas fa-sync me-1"></i>Refresh
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-info">
                            <i class="fas fa-calculator me-2"></i>
                            <strong>Scoring Formula:</strong> (Total Yes Votes / Total Possible Yes Votes) × 100<br>
                            <small>Maximum possible: 7 criteria × number of judges = 100%</small>
                        </div>
                        <div id="leaderboard-content">
                            <div class="text-center">
                                <div class="spinner-border text-success" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading leaderboard...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Teams Tab -->
            <div class="tab-pane fade" id="teams" role="tabpanel">
                <div class="card">
                    <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-users me-2"></i>
                            Competition Teams
                        </h5>
                        <button class="btn btn-light btn-sm" onclick="loadTeams()">
                            <i class="fas fa-sync me-1"></i>Refresh
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="teams-content">
                            <div class="text-center">
                                <div class="spinner-border text-info" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading teams...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Judges Tab -->
            <div class="tab-pane fade" id="judges" role="tabpanel">
                <div class="card">
                    <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-user-tie me-2"></i>
                            Competition Judges
                        </h5>
                        <button class="btn btn-dark btn-sm" onclick="loadJudges()">
                            <i class="fas fa-sync me-1"></i>Refresh
                        </button>
                    </div>
                    <div class="card-body">
                        <div id="judges-content">
                            <div class="text-center">
                                <div class="spinner-border text-warning" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading judges...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Documentation Tab -->
            <div class="tab-pane fade" id="documentation" role="tabpanel">
                <div class="card">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-book me-2"></i>
                            Competition Documentation
                        </h5>
                    </div>
                    <div class="card-body documentation">
                        <h4>Ignite Innovative GenAI Training - Voting Structure</h4>
                        
                        <h5 class="mt-4">Introduction</h5>
                        <p>This competition aims to evaluate teams' ability to leverage AWS GenAI services in solving real customer problems. Teams will be judged on their understanding of customer needs, solution design, and presentation skills.</p>
                        
                        <h5 class="mt-4">Competition Objectives</h5>
                        <p>Teams must demonstrate their ability to:</p>
                        <ul>
                            <li>Understand customer problems deeply</li>
                            <li>Define success criteria collaboratively with customers</li>
                            <li>Present relevant demos that validate solutions</li>
                            <li>Correlate demos with actual PoC services</li>
                            <li>Leverage AWS GenAI services effectively</li>
                            <li>Collaborate effectively as a team</li>
                            <li>Take notes to address unanswered questions</li>
                        </ul>
                        
                        <h5 class="mt-4">Scoring Criteria (Yes/No Questions)</h5>
                        
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>1. Problem Understanding (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team demonstrate deep understanding of the customer's problem?</p>
                                        <p><strong>Yes:</strong> Team clearly articulated the problem, its impact, and root causes</p>
                                        <p><strong>No:</strong> Problem understanding was superficial or unclear</p>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>2. Success Criteria Definition (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team determine success criteria collaboratively with the customer?</p>
                                        <p><strong>Yes:</strong> Clear evidence of customer collaboration in defining measurable outcomes</p>
                                        <p><strong>No:</strong> Success criteria were defined unilaterally or are vague</p>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>3. Demo Relevance (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team present a demo that directly addresses the customer problem?</p>
                                        <p><strong>Yes:</strong> Demo clearly validates the proposed solution approach</p>
                                        <p><strong>No:</strong> Demo was generic or didn't address the specific problem</p>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>4. Service Correlation (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team effectively correlate the demo with AWS services for the PoC?</p>
                                        <p><strong>Yes:</strong> Clear mapping between demo components and proposed PoC architecture</p>
                                        <p><strong>No:</strong> Weak or missing connection between demo and PoC services</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>5. GenAI Services Usage (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team leverage AWS GenAI services appropriately?</p>
                                        <p><strong>Yes:</strong> Meaningful integration of GenAI services that add value to the solution</p>
                                        <p><strong>No:</strong> No GenAI services used or inappropriate/forced usage</p>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-header bg-warning text-dark">
                                        <strong>6. Team Collaboration (Weight: 10%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team demonstrate effective collaboration during the presentation?</p>
                                        <p><strong>Yes:</strong> All team members actively contributed and demonstrated complementary roles</p>
                                        <p><strong>No:</strong> Limited participation or uneven contribution from team members</p>
                                    </div>
                                </div>
                                
                                <div class="card mb-3">
                                    <div class="card-header bg-primary text-white">
                                        <strong>7. Notes of Unanswered Questions (Weight: 15%)</strong>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Question:</strong> Did the team take notes of the unanswered questions to address later?</p>
                                        <p><strong>Yes:</strong> They have taken notes and did not assume answers based on their assumptions</p>
                                        <p><strong>No:</strong> Did not take notes of unanswered questions or answered without knowledge</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h5 class="mt-4">Scoring Methodology</h5>
                        
                        <div class="alert alert-info">
                            <h6>Judge Scoring:</h6>
                            <ul class="mb-0">
                                <li>Each judge answers Yes/No for all 7 criteria</li>
                                <li>Yes = 1 point, No = 0 points</li>
                                <li>Maximum score per judge: 7 points</li>
                            </ul>
                        </div>
                        
                        <div class="alert alert-success">
                            <h6>Final Team Score Calculation:</h6>
                            <ul class="mb-0">
                                <li>Sum all "Yes" responses from all judges</li>
                                <li>Calculate percentage: <strong>(Total Yes / Total Possible Yes) × 100</strong></li>
                                <li>Maximum possible score: 21 points (7 criteria × 3 judges)</li>
                                <li>Final percentage determines ranking</li>
                            </ul>
                        </div>
                        
                        <h6>Example Scoring</h6>
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Judge</th>
                                    <th>Yes Votes</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Judge 1</td>
                                    <td>6/7 Yes</td>
                                </tr>
                                <tr>
                                    <td>Judge 2</td>
                                    <td>5/7 Yes</td>
                                </tr>
                                <tr>
                                    <td>Judge 3</td>
                                    <td>7/7 Yes</td>
                                </tr>
                                <tr class="table-success">
                                    <td><strong>Total</strong></td>
                                    <td><strong>18/21</strong></td>
                                </tr>
                                <tr class="table-warning">
                                    <td><strong>Final Score</strong></td>
                                    <td><strong>85.7%</strong></td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <h5 class="mt-4">Tiebreaker Protocol</h5>
                        <p>In case of a tied score:</p>
                        <ol>
                            <li>Compare weighted scores based on criteria importance</li>
                            <li>Priority given to higher scores in:
                                <ul>
                                    <li>Problem Understanding (15%)</li>
                                    <li>Success Criteria Definition (15%)</li>
                                    <li>Demo Relevance (15%)</li>
                                    <li>Service Correlation (15%)</li>
                                    <li>GenAI Services Usage (15%)</li>
                                    <li>Notes of Unanswered Questions (15%)</li>
                                    <li>Team Collaboration (10%)</li>
                                </ul>
                            </li>
                        </ol>
                        
                        <h5 class="mt-4">Deliverables Required from Teams</h5>
                        <ul>
                            <li>Customer problem statement (max 200 words)</li>
                            <li>Success criteria definition process documentation</li>
                            <li>Demo recording or live presentation (15-20 minutes)</li>
                            <li>AWS services architecture diagram for PoC</li>
                            <li>GenAI services integration plan</li>
                        </ul>
                        
                        <h5 class="mt-4">Submission Guidelines</h5>
                        <ul>
                            <li>All deliverables must be submitted by [Insert Deadline]</li>
                            <li>Presentations/demos should not exceed 20 minutes</li>
                            <li>Submit all materials in PDF format, except for demo recordings (MP4 format accepted)</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Admin Tab -->
            <div class="tab-pane fade" id="admin" role="tabpanel">
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-plus me-2"></i>Add New Team
                                </h6>
                            </div>
                            <div class="card-body">
                                <form id="add-team-form">
                                    <div class="mb-3">
                                        <label for="team-name" class="form-label">Team Name *</label>
                                        <input type="text" class="form-control" id="team-name" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="team-description" class="form-label">Description</label>
                                        <textarea class="form-control" id="team-description" rows="3" placeholder="Customer problem statement (max 200 words)"></textarea>
                                    </div>
                                    <button type="submit" class="btn btn-primary">
                                        <i class="fas fa-plus me-1"></i>Add Team
                                    </button>
                                </form>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header bg-info text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-user-plus me-2"></i>Add New Judge
                                </h6>
                            </div>
                            <div class="card-body">
                                <form id="add-judge-form">
                                    <div class="mb-3">
                                        <label for="judge-name" class="form-label">Judge Name *</label>
                                        <input type="text" class="form-control" id="judge-name" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="judge-email" class="form-label">Email *</label>
                                        <input type="email" class="form-control" id="judge-email" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="judge-role" class="form-label">Role</label>
                                        <input type="text" class="form-control" id="judge-role" placeholder="e.g., Senior AI Researcher">
                                    </div>
                                    <button type="submit" class="btn btn-info">
                                        <i class="fas fa-user-plus me-1"></i>Add Judge
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header bg-secondary text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-cogs me-2"></i>System Management
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="d-grid gap-2">
                                    <button type="button" class="btn btn-info" onclick="manualRefresh()">
                                        <i class="fas fa-sync me-1"></i>Refresh All Data
                                    </button>
                                    <button type="button" class="btn btn-warning" onclick="clearAllSampleData()">
                                        <i class="fas fa-trash me-1"></i>Clear All Data & Reset Criteria
                                    </button>
                                </div>
                                <hr>
                                <small class="text-muted">
                                    <i class="fas fa-info-circle me-1"></i>
                                    "Clear All Data" will reset criteria with correct weights (15% each, except Team Collaboration 10%).
                                </small>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header bg-dark text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-chart-bar me-2"></i>System Status
                                </h6>
                            </div>
                            <div class="card-body">
                                <div id="system-status">
                                    <div class="text-center">
                                        <div class="spinner-border text-dark" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                        <p class="mt-2">Loading status...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Global variables
        let currentData = { teams: [], judges: [], criteria: [] };
        
        // API helper function with correct path
        async function apiCall(endpoint, options = {}) {
            const url = endpoint.startsWith('/') ? `/Prod/api${endpoint}` : `/Prod/api/${endpoint}`;
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        }
        
        // Load initial data
        async function loadInitialData() {
            try {
                console.log('Loading initial data...');
                const [teams, judges, criteria] = await Promise.all([
                    apiCall('/teams'),
                    apiCall('/judges'),
                    apiCall('/criteria')
                ]);
                
                console.log('Initial data loaded:', { teams: teams.length, judges: judges.length, criteria: criteria.length });
                currentData = { teams, judges, criteria };
                
                // Update all interfaces
                loadVotingInterface();
                updateSystemStatus();
                
                // Refresh visible tabs
                const activeTab = document.querySelector('.tab-pane.active, .tab-pane.show');
                if (activeTab) {
                    const tabId = activeTab.id;
                    if (tabId === 'teams') {
                        loadTeams();
                    } else if (tabId === 'judges') {
                        loadJudges();
                    } else if (tabId === 'leaderboard') {
                        loadLeaderboard();
                    }
                }
                
            } catch (error) {
                console.error('Error loading initial data:', error);
                showError('Failed to load initial data: ' + error.message);
            }
        }
        
        // Load voting interface
        function loadVotingInterface() {
            const container = document.getElementById('voting-interface');
            
            if (currentData.judges.length === 0 || currentData.teams.length === 0) {
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>Setup Required:</strong> Please add teams and judges in the Admin tab before voting can begin.
                    </div>
                `;
                return;
            }
            
            container.innerHTML = `
                <form id="voting-form">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="judge-select" class="form-label">Select Judge *</label>
                                <select class="form-select" id="judge-select" required>
                                    <option value="">Choose a judge...</option>
                                    ${currentData.judges.map(judge => 
                                        `<option value="${judge.id}">${judge.name} (${judge.email})</option>`
                                    ).join('')}
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="team-select" class="form-label">Select Team *</label>
                                <select class="form-select" id="team-select" required>
                                    <option value="">Choose a team...</option>
                                    ${currentData.teams.map(team => 
                                        `<option value="${team.id}">${team.name}</option>`
                                    ).join('')}
                                </select>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <h6>Evaluation Criteria (Yes/No Questions):</h6>
                        <div id="criteria-voting">
                            ${currentData.criteria.map(criteria => `
                                <div class="card mb-2">
                                    <div class="card-body">
                                        <div class="row align-items-center">
                                            <div class="col-md-5">
                                                <strong>${criteria.name}</strong>
                                                <small class="text-muted d-block">Weight: ${criteria.weight}%</small>
                                                ${criteria.description ? `<small class="text-info">${criteria.description}</small>` : ''}
                                            </div>
                                            <div class="col-md-4">
                                                <div class="btn-group" role="group">
                                                    <input type="radio" class="btn-check" name="criteria_${criteria.id}" id="yes_${criteria.id}" value="1">
                                                    <label class="btn btn-outline-success" for="yes_${criteria.id}">
                                                        <i class="fas fa-check me-1"></i>Yes
                                                    </label>
                                                    
                                                    <input type="radio" class="btn-check" name="criteria_${criteria.id}" id="no_${criteria.id}" value="0">
                                                    <label class="btn btn-outline-danger" for="no_${criteria.id}">
                                                        <i class="fas fa-times me-1"></i>No
                                                    </label>
                                                </div>
                                            </div>
                                            <div class="col-md-3">
                                                <input type="text" class="form-control form-control-sm" placeholder="Comments (optional)" id="comments_${criteria.id}">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="fas fa-vote-yea me-2"></i>Submit All Votes
                        </button>
                    </div>
                </form>
            `;
            
            // Add form submission handler
            document.getElementById('voting-form').addEventListener('submit', handleVoteSubmission);
        }
        
        // Handle vote submission
        async function handleVoteSubmission(event) {
            event.preventDefault();
            
            const judgeId = document.getElementById('judge-select').value;
            const teamId = document.getElementById('team-select').value;
            
            if (!judgeId || !teamId) {
                alert('Please select both a judge and a team.');
                return;
            }
            
            const submitButton = event.target.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
            submitButton.disabled = true;
            
            try {
                const votes = [];
                
                for (const criteria of currentData.criteria) {
                    const selectedValue = document.querySelector(`input[name="criteria_${criteria.id}"]:checked`);
                    if (selectedValue) {
                        const comments = document.getElementById(`comments_${criteria.id}`).value;
                        
                        const voteData = {
                            judge_id: judgeId,
                            team_id: teamId,
                            criteria_id: criteria.id,
                            score: parseInt(selectedValue.value),
                            comments: comments
                        };
                        
                        await apiCall('/vote', {
                            method: 'POST',
                            body: JSON.stringify(voteData)
                        });
                        
                        votes.push(voteData);
                    }
                }
                
                if (votes.length === 0) {
                    alert('Please vote on at least one criterion.');
                    return;
                }
                
                alert(`Successfully submitted ${votes.length} votes!`);
                
                // Reset form
                event.target.reset();
                
                // Refresh leaderboard if visible
                if (document.getElementById('leaderboard').classList.contains('show')) {
                    loadLeaderboard();
                }
                
            } catch (error) {
                console.error('Error submitting votes:', error);
                alert('Failed to submit votes: ' + error.message);
            } finally {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        }
        
        // Load teams
        async function loadTeams() {
            const container = document.getElementById('teams-content');
            
            try {
                const teams = await apiCall('/teams');
                
                if (teams.length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No teams found. Add teams in the Admin tab.
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="row">
                        ${teams.map(team => `
                            <div class="col-md-6 mb-3">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title">
                                            <i class="fas fa-users me-2 text-primary"></i>
                                            ${team.name}
                                        </h5>
                                        <p class="card-text">${team.description || 'No description provided'}</p>
                                        <small class="text-muted">
                                            <i class="fas fa-trophy me-1"></i>
                                            Competition: ${team.competition_name || 'Ignite Innovative GenAI Training'}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading teams:', error);
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load teams: ${error.message}
                    </div>
                `;
            }
        }
        
        // Load judges
        async function loadJudges() {
            const container = document.getElementById('judges-content');
            
            try {
                const judges = await apiCall('/judges');
                
                if (judges.length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No judges found. Add judges in the Admin tab.
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="row">
                        ${judges.map(judge => `
                            <div class="col-md-6 mb-3">
                                <div class="card">
                                    <div class="card-body">
                                        <h5 class="card-title">
                                            <i class="fas fa-user-tie me-2 text-warning"></i>
                                            ${judge.name}
                                        </h5>
                                        <p class="card-text">
                                            <i class="fas fa-envelope me-1"></i>
                                            ${judge.email}
                                        </p>
                                        <small class="text-muted">
                                            <i class="fas fa-briefcase me-1"></i>
                                            ${judge.role || 'Judge'}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading judges:', error);
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load judges: ${error.message}
                    </div>
                `;
            }
        }
        
        // Load leaderboard with CORRECTED scoring display
        async function loadLeaderboard() {
            const container = document.getElementById('leaderboard-content');
            
            try {
                const leaderboard = await apiCall('/leaderboard');
                
                if (leaderboard.length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No votes submitted yet. Start voting to see the leaderboard!
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = `
                    <div class="row">
                        ${leaderboard.map((team, index) => `
                            <div class="col-12 mb-3">
                                <div class="card leaderboard-item ${index === 0 ? 'border-warning' : ''}">
                                    <div class="card-body">
                                        <div class="row align-items-center">
                                            <div class="col-md-1 text-center">
                                                <span class="badge ${index === 0 ? 'bg-warning text-dark' : index === 1 ? 'bg-secondary' : index === 2 ? 'bg-info' : 'bg-light text-dark'} score-badge">
                                                    ${index === 0 ? '<i class="fas fa-crown"></i>' : '#' + (index + 1)}
                                                </span>
                                            </div>
                                            <div class="col-md-4">
                                                <h5 class="mb-1">${team.team_name}</h5>
                                                <small class="text-muted">${team.description || ''}</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-success score-badge">
                                                    ${team.final_percentage.toFixed(1)}%
                                                </div>
                                                <small class="d-block text-muted">Final Score</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-primary score-badge">
                                                    ${team.total_yes_votes}/${team.total_possible_yes}
                                                </div>
                                                <small class="d-block text-muted">Yes Votes</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-info score-badge">
                                                    ${team.judge_count}
                                                </div>
                                                <small class="d-block text-muted">Judges</small>
                                            </div>
                                            <div class="col-md-1 text-center">
                                                <div class="badge bg-secondary">
                                                    ${team.vote_count}
                                                </div>
                                                <small class="d-block text-muted">Total Votes</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading leaderboard:', error);
                container.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load leaderboard: ${error.message}
                    </div>
                `;
            }
        }
        
        // Update system status
        async function updateSystemStatus() {
            const container = document.getElementById('system-status');
            
            try {
                const debugData = await apiCall('/debug-db');
                const counts = debugData.counts;
                
                container.innerHTML = `
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="badge bg-primary fs-6 mb-1">${counts.teams}</div>
                            <div class="small">Teams</div>
                        </div>
                        <div class="col-6">
                            <div class="badge bg-info fs-6 mb-1">${counts.judges}</div>
                            <div class="small">Judges</div>
                        </div>
                        <div class="col-6 mt-2">
                            <div class="badge bg-success fs-6 mb-1">${counts.votes}</div>
                            <div class="small">Votes</div>
                        </div>
                        <div class="col-6 mt-2">
                            <div class="badge bg-warning text-dark fs-6 mb-1">${counts.criteria}</div>
                            <div class="small">Criteria</div>
                        </div>
                    </div>
                    <hr>
                    <div class="text-center">
                        <span class="badge bg-success">
                            <i class="fas fa-database me-1"></i>DynamoDB Active
                        </span>
                        <span class="badge bg-info">
                            <i class="fas fa-calculator me-1"></i>Corrected Formula
                        </span>
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading system status:', error);
                container.innerHTML = `
                    <div class="alert alert-danger small">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        Status unavailable
                    </div>
                `;
            }
        }
        
        // Add team
        document.getElementById('add-team-form').addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const name = document.getElementById('team-name').value.trim();
            const description = document.getElementById('team-description').value.trim();
            
            if (!name) {
                alert('Team name is required.');
                return;
            }
            
            const submitButton = event.target.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
            submitButton.disabled = true;
            
            try {
                await apiCall('/teams', {
                    method: 'POST',
                    body: JSON.stringify({ name, description })
                });
                
                alert('Team added successfully!');
                event.target.reset();
                
                // Refresh data
                await loadInitialData();
                
                // Refresh teams tab if visible
                if (document.getElementById('teams').classList.contains('show')) {
                    loadTeams();
                }
                
            } catch (error) {
                console.error('Error adding team:', error);
                alert('Failed to add team: ' + error.message);
            } finally {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        });
        
        // Add judge
        document.getElementById('add-judge-form').addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const name = document.getElementById('judge-name').value.trim();
            const email = document.getElementById('judge-email').value.trim();
            const role = document.getElementById('judge-role').value.trim();
            
            if (!name || !email) {
                alert('Name and email are required.');
                return;
            }
            
            const submitButton = event.target.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
            submitButton.disabled = true;
            
            try {
                await apiCall('/judges', {
                    method: 'POST',
                    body: JSON.stringify({ name, email, role })
                });
                
                alert('Judge added successfully!');
                event.target.reset();
                
                // Refresh data
                await loadInitialData();
                
                // Refresh judges tab if visible
                if (document.getElementById('judges').classList.contains('show')) {
                    loadJudges();
                }
                
            } catch (error) {
                console.error('Error adding judge:', error);
                alert('Failed to add judge: ' + error.message);
            } finally {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        });
        
        // Manual refresh
        async function manualRefresh() {
            try {
                console.log('Manual refresh triggered');
                
                // Show loading state
                const refreshBtn = event.target;
                const originalText = refreshBtn.innerHTML;
                refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
                refreshBtn.disabled = true;
                
                // Force reload all data
                await loadInitialData();
                
                // Show success message
                alert('Data refreshed successfully!');
                
                // Restore button
                refreshBtn.innerHTML = originalText;
                refreshBtn.disabled = false;
                
            } catch (error) {
                console.error('Error during manual refresh:', error);
                alert(`Refresh failed: ${error.message}`);
                
                // Restore button even on error
                const refreshBtn = event.target;
                refreshBtn.innerHTML = '<i class="fas fa-sync"></i> Refresh All Data';
                refreshBtn.disabled = false;
            }
        }
        
        // Clear all data
        async function clearAllSampleData() {
            if (!confirm('Are you sure you want to delete ALL teams, judges, and votes? This will completely reset the system and reinitialize criteria with correct weights.')) {
                return;
            }
            
            if (!confirm('This is your final warning. ALL DATA will be permanently deleted and criteria will be reset with correct weights (15% each, except Team Collaboration 10%). Continue?')) {
                return;
            }
            
            try {
                const result = await apiCall('/clear-sample-data', {
                    method: 'POST'
                });
                
                console.log('All data cleared:', result);
                alert(`Success! ${result.message}\\n\\nDeleted: ${result.deleted_teams} teams, ${result.deleted_judges} judges, ${result.deleted_votes} votes.`);
                
                // Force refresh currentData from server
                console.log('Forcing refresh of currentData...');
                currentData = { teams: [], judges: [], criteria: [] };
                
                // Force reload all data from server (this will reinitialize criteria)
                await loadInitialData();
                
                // Force refresh all visible tabs
                const activeTab = document.querySelector('.tab-pane.active, .tab-pane.show');
                if (activeTab) {
                    const tabId = activeTab.id;
                    console.log(`Refreshing active tab: ${tabId}`);
                    if (tabId === 'teams') {
                        loadTeams();
                    } else if (tabId === 'judges') {
                        loadJudges();
                    } else if (tabId === 'leaderboard') {
                        loadLeaderboard();
                    }
                }
                
                console.log('Clear operation completed successfully');
                
            } catch (error) {
                console.error('Error clearing all data:', error);
                alert(`Failed to clear data: ${error.message}`);
            }
        }
        
        // Show error message
        function showError(message) {
            const alertHtml = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Error:</strong> ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            // Insert at the top of the container
            const container = document.querySelector('.container');
            container.insertAdjacentHTML('afterbegin', alertHtml);
        }
        
        // Tab change handlers
        document.addEventListener('shown.bs.tab', function (event) {
            const targetId = event.target.getAttribute('data-bs-target').substring(1);
            
            switch (targetId) {
                case 'teams':
                    loadTeams();
                    break;
                case 'judges':
                    loadJudges();
                    break;
                case 'leaderboard':
                    loadLeaderboard();
                    break;
                case 'admin':
                    updateSystemStatus();
                    break;
            }
        });
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Page loaded, initializing...');
            loadInitialData();
        });
        
    </script>
</body>
</html>'''
    }

# Replace the main file
mv app_dynamodb_fixed.py app_dynamodb.py
