import json
import boto3
import os
import logging
import base64
from decimal import Decimal
from datetime import datetime
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')

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

def get_base64_image(filename):
    """Convert image file to base64 string"""
    try:
        with open(filename, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error loading image {filename}: {str(e)}")
        return ""

def send_vote_confirmation_email(judge_email, judge_name, team_name, votes_data):
    """Send vote confirmation email to judge using Amazon SES"""
    try:
        # Create email content
        subject = f"Vote Confirmation - FSI 3 Hackaton GenAI Training"
        
        # Create HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .vote-summary {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; }}
                .criteria-item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
                .vote-yes {{ color: #28a745; font-weight: bold; }}
                .vote-no {{ color: #dc3545; font-weight: bold; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏆 Vote Confirmation</h1>
                <h2>FSI 3 Hackaton GenAI Training</h2>
            </div>
            
            <div class="content">
                <p>Dear <strong>{judge_name}</strong>,</p>
                
                <p>Thank you for submitting your votes! This email confirms your evaluation for:</p>
                
                <div class="vote-summary">
                    <h3>🎯 Team: {team_name}</h3>
                    <p><strong>Submission Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Total Criteria Evaluated:</strong> {len(votes_data)}</p>
                </div>
                
                <h3>📊 Your Votes:</h3>
        """
        
        # Add each vote to the email
        for vote in votes_data:
            vote_display = "✅ YES" if vote['score'] == 1 else "❌ NO"
            vote_class = "vote-yes" if vote['score'] == 1 else "vote-no"
            comments = vote.get('comments', 'No comments')
            
            html_body += f"""
                <div class="criteria-item">
                    <strong>{vote['criteria_name']}</strong><br>
                    <span class="{vote_class}">Vote: {vote_display}</span><br>
                    <em>Comments: {comments}</em>
                </div>
            """
        
        html_body += f"""
                <p>Your votes have been successfully recorded in the competition system.</p>
                
                <p>Best regards,<br>
                <strong>FSI 3 Hackaton GenAI Training Team</strong></p>
            </div>
            
            <div class="footer">
                <p>This is an automated confirmation email from the FSI 3 Hackaton GenAI Training voting system.</p>
                <p>Powered by AWS - Amazon SES</p>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_body = f"""
Vote Confirmation - FSI 3 Hackaton GenAI Training

Dear {judge_name},

Thank you for submitting your votes! This email confirms your evaluation for:

Team: {team_name}
Submission Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Total Criteria Evaluated: {len(votes_data)}

Your Votes:
"""
        
        for vote in votes_data:
            vote_display = "YES" if vote['score'] == 1 else "NO"
            comments = vote.get('comments', 'No comments')
            text_body += f"""
- {vote['criteria_name']}: {vote_display}
  Comments: {comments}
"""
        
        text_body += f"""
Your votes have been successfully recorded in the competition system.

Best regards,
FSI 3 Hackaton GenAI Training Team

---
This is an automated confirmation email from the FSI 3 Hackaton GenAI Training voting system.
Powered by AWS - Amazon SES
        """
        
        # Send email using SES
        response = ses_client.send_email(
            Source='mincarelli@mincarelli.com.br',  # Using verified personal domain
            Destination={
                'ToAddresses': [judge_email]
            },
            ReplyToAddresses=['mincarelli@mincarelli.com.br'],
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        logger.info(f"Email sent successfully to {judge_email}. MessageId: {response['MessageId']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {judge_email}: {str(e)}")
        return False

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
    """Initialize DynamoDB tables with criteria"""
    try:
        # Initialize criteria (always needed)
        criteria_response = criteria_table.scan(Select='COUNT')
        if criteria_response['Count'] == 0:
            criteria_data = [
                {"id": "1", "name": "Problem Understanding", "weight": Decimal('15'), "max_score": 1},
                {"id": "2", "name": "Success Criteria Definition", "weight": Decimal('15'), "max_score": 1},
                {"id": "3", "name": "Demo Relevance", "weight": Decimal('15'), "max_score": 1},
                {"id": "4", "name": "Service Correlation", "weight": Decimal('15'), "max_score": 1},
                {"id": "5", "name": "GenAI Services Usage", "weight": Decimal('15'), "max_score": 1},
                {"id": "6", "name": "Team Collaboration", "weight": Decimal('10'), "max_score": 1},
                {"id": "7", "name": "Notes of Unanswered Questions", "weight": Decimal('15'), "max_score": 1}
            ]
            
            for criteria in criteria_data:
                criteria_table.put_item(Item=criteria)
            logger.info("Added criteria")
        
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
            problem_statement = body.get('problem_statement', '').strip()
            success_criteria = body.get('success_criteria', '').strip()
            
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
                'problem_statement': problem_statement,
                'success_criteria': success_criteria,
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
        
        elif method == 'POST' and path == '/criteria':
            body = json.loads(event.get('body', '{}'))
            name = body.get('name', '').strip()
            weight = body.get('weight', 0)
            description = body.get('description', '').strip()
            
            if not name or not weight:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Criteria name and weight are required'})
                }
            
            # Generate new criteria ID
            existing_criteria = criteria_table.scan()['Items']
            max_id = max([int(c['id']) for c in existing_criteria] + [0])
            new_id = str(max_id + 1)
            
            criteria = {
                'id': new_id,
                'name': name,
                'weight': Decimal(str(weight)),
                'max_score': 1,
                'description': description,
                'created_at': datetime.now().isoformat()
            }
            
            criteria_table.put_item(Item=criteria)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({'id': new_id, 'name': name, 'weight': weight, 'description': description, 'message': 'Criteria added successfully'})
            }
        
        elif method == 'DELETE' and path.startswith('/criteria/'):
            criteria_id = path.split('/')[-1]
            
            if not criteria_id:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Criteria ID is required'})
                }
            
            # Check if criteria exists
            try:
                criteria_table.get_item(Key={'id': criteria_id})['Item']
            except KeyError:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Criteria not found'})
                }
            
            # Delete all votes for this criteria first
            votes_response = votes_table.scan()
            deleted_votes = 0
            for vote in votes_response['Items']:
                if vote['criteria_id'] == criteria_id:
                    votes_table.delete_item(Key={'id': vote['id']})
                    deleted_votes += 1
            
            # Delete the criteria
            criteria_table.delete_item(Key={'id': criteria_id})
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({
                    'message': 'Criteria deleted successfully',
                    'criteria_id': criteria_id,
                    'deleted_votes': deleted_votes
                })
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
        
        elif method == 'POST' and path == '/submit-votes':
            # New endpoint for batch vote submission with email notification
            body = json.loads(event.get('body', '{}'))
            judge_id = str(body.get('judge_id', ''))
            team_id = str(body.get('team_id', ''))
            votes_data = body.get('votes', [])
            overwrite_existing = body.get('overwrite_existing', False)
            
            if not judge_id or not team_id or not votes_data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Judge ID, Team ID, and votes data are required'})
                }
            
            try:
                # Check for existing votes by this judge for this team
                existing_votes_response = votes_table.query(
                    IndexName='judge-index',
                    KeyConditionExpression='judge_id = :judge_id',
                    ExpressionAttributeValues={':judge_id': judge_id}
                )
                
                existing_votes_for_team = [
                    vote for vote in existing_votes_response['Items'] 
                    if vote['team_id'] == team_id
                ]
                
                # If votes exist and overwrite is not explicitly allowed, return warning
                if existing_votes_for_team and not overwrite_existing:
                    return {
                        'statusCode': 409,  # Conflict status code
                        'headers': {'Content-Type': 'application/json', **get_security_headers()},
                        'body': json.dumps({
                            'error': 'duplicate_votes',
                            'message': 'You have already voted for this team',
                            'existing_votes_count': len(existing_votes_for_team),
                            'existing_votes_date': existing_votes_for_team[0]['created_at'] if existing_votes_for_team else None,
                            'requires_confirmation': True
                        })
                    }
                
                # Get judge and team information for email
                judge_response = judges_table.get_item(Key={'id': judge_id})
                team_response = teams_table.get_item(Key={'id': team_id})
                criteria_response = criteria_table.scan()
                
                if 'Item' not in judge_response or 'Item' not in team_response:
                    return {
                        'statusCode': 404,
                        'headers': {'Content-Type': 'application/json', **get_security_headers()},
                        'body': json.dumps({'error': 'Judge or team not found'})
                    }
                
                judge = judge_response['Item']
                team = team_response['Item']
                criteria_dict = {c['id']: c for c in criteria_response['Items']}
                
                # If overwriting, delete existing votes first
                deleted_votes_count = 0
                if existing_votes_for_team and overwrite_existing:
                    for existing_vote in existing_votes_for_team:
                        votes_table.delete_item(Key={'id': existing_vote['id']})
                        deleted_votes_count += 1
                
                # Submit all new votes
                submitted_votes = []
                for vote_data in votes_data:
                    vote_id = str(uuid.uuid4())
                    vote = {
                        'id': vote_id,
                        'judge_id': judge_id,
                        'team_id': team_id,
                        'criteria_id': vote_data['criteria_id'],
                        'score': Decimal(str(vote_data['score'])),
                        'comments': vote_data.get('comments', ''),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    votes_table.put_item(Item=vote)
                    
                    # Prepare vote data for email
                    criteria = criteria_dict.get(vote_data['criteria_id'], {})
                    submitted_votes.append({
                        'criteria_name': criteria.get('name', 'Unknown Criteria'),
                        'score': vote_data['score'],
                        'comments': vote_data.get('comments', '')
                    })
                
                # Send confirmation email
                email_sent = send_vote_confirmation_email(
                    judge_email=judge['email'],
                    judge_name=judge['name'],
                    team_name=team['name'],
                    votes_data=submitted_votes
                )
                
                response_data = {
                    'message': 'Votes submitted successfully',
                    'votes_count': len(submitted_votes),
                    'email_sent': email_sent,
                    'judge_email': judge['email']
                }
                
                # Add overwrite information if applicable
                if deleted_votes_count > 0:
                    response_data['overwritten_votes'] = deleted_votes_count
                    response_data['action'] = 'overwrite'
                else:
                    response_data['action'] = 'new'
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps(response_data)
                }
                
            except Exception as e:
                logger.error(f"Error in batch vote submission: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', **get_security_headers()},
                    'body': json.dumps({'error': 'Internal server error'})
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
            # Get all data
            teams_response = teams_table.scan()
            votes_response = votes_table.scan()
            criteria_response = criteria_table.scan()
            
            teams = teams_response['Items']
            votes = votes_response['Items']
            criteria = criteria_response['Items']
            
            # Create criteria lookup
            criteria_dict = {c['id']: c for c in criteria}
            
            # Calculate scores for each team
            team_scores = {}
            for team in teams:
                team_id = team['id']
                team_votes = [v for v in votes if v['team_id'] == team_id]
                
                total_score = 0
                vote_count = len(team_votes)
                judge_count = len(set(v['judge_id'] for v in team_votes))
                
                for vote in team_votes:
                    # Total score = simple sum of Yes votes (1 for Yes, 0 for No)
                    total_score += float(vote['score'])
                
                average_score = sum(float(v['score']) for v in team_votes) / vote_count if vote_count > 0 else 0
                # Calculate average percentage across judges
                judge_percentages = []
                for judge_id in set(v["judge_id"] for v in team_votes):
                    judge_votes_list = [v for v in team_votes if v["judge_id"] == judge_id]
                    judge_yes = sum(1 for v in judge_votes_list if float(v["score"]) == 1)
                    judge_total = len(judge_votes_list)
                    if judge_total > 0:
                        judge_percentages.append((judge_yes / judge_total) * 100)
                weighted_percentage = sum(judge_percentages) / len(judge_percentages) if judge_percentages else 0
                
                # Calculate total Yes votes across all judges
                total_yes_votes = sum(1 for v in team_votes if float(v["score"]) == 1)
                total_possible_votes = len(team_votes)
                
                team_scores[team_id] = {
                    'id': team['id'],
                    'team_name': team['name'],
                    'description': team.get('description', ''),
                    'total_yes_votes': total_yes_votes,
                    'total_possible_votes': total_possible_votes,
                    'total_score': total_score,
                    'average_score': average_score,
                    'vote_count': vote_count,
                    'judge_count': judge_count,
                    'weighted_percentage': weighted_percentage
                }
            
            # Sort by total score descending
            leaderboard = sorted(team_scores.values(), 
                               key=lambda x: (x['total_score'], x['weighted_percentage'], x['average_score']), 
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
            
            # Set clear flags
            settings_table.put_item(Item={'key': 'sample_data_cleared', 'value': 'true'})
            settings_table.put_item(Item={'key': 'data_cleared_at', 'value': datetime.now().isoformat()})
            settings_table.put_item(Item={'key': 'user_managed', 'value': 'true'})
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', **get_security_headers()},
                'body': json.dumps({
                    'message': 'All data cleared successfully',
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
            criteria = [{'id': c['id'], 'name': c['name']} for c in criteria_response['Items']]
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
    """Serve the complete voting application with full interface"""
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
        .logo-container {
            transition: transform 0.3s ease;
        }
        .logo-container:hover {
            transform: scale(1.05);
        }
        .logo-container svg {
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
        }
        .fsi-banner {
            background: linear-gradient(135deg, #FF9900 0%, #232F3E 100%);
            color: white;
            border-bottom: 3px solid #232F3E;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .fsi-title {
            font-size: 2.5rem;
            font-weight: bold;
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .hackaton-title {
            font-size: 2rem;
            font-weight: bold;
            color: white;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            letter-spacing: 2px;
        }
        .powered-by {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 500;
        }
        .ignite-sticker-rocket {
            transition: transform 0.3s ease;
        }
        .ignite-sticker-rocket:hover {
            transform: scale(1.05);
        }
        .ignite-sticker-rocket img {
            filter: drop-shadow(0 0 15px rgba(255, 153, 0, 0.8)) drop-shadow(0 0 25px rgba(255, 153, 0, 0.5));
            border-radius: 10px;
        }
        .ignite-sticker-flame {
            transition: transform 0.3s ease;
        }
        .ignite-sticker-flame:hover {
            transform: scale(1.05);
        }
        .ignite-sticker-flame img {
            filter: drop-shadow(0 0 15px rgba(255, 215, 0, 0.8)) drop-shadow(0 0 25px rgba(255, 215, 0, 0.5));
            border-radius: 10px;
        }
        .auto-expand-textarea {
            transition: height 0.2s ease;
            line-height: 1.4;
        }
        .auto-expand-textarea:focus {
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
            border-color: #667eea;
        }
        @media (max-width: 768px) {
            .fsi-title {
                font-size: 1.8rem;
            }
            .hackaton-title {
                font-size: 1.4rem;
                letter-spacing: 1px;
            }
            .powered-by {
                font-size: 0.8rem;
            }
            .ignite-sticker-flame img {
                width: 120px;
                height: 120px;
            }
            .ignite-sticker-rocket img {
                width: 120px;
                height: 120px;
            }
        }
    </style>
</head>
<body>
    <!-- FSI 3 Hackaton GenAI Full-Width Banner -->
    <div class="fsi-banner">
        <div class="container-fluid">
            <div class="row align-items-center py-3">
                <div class="col-md-3 text-start">
                    <h2 class="fsi-title mb-0">FSI 3</h2>
                </div>
                <div class="col-md-6 text-center">
                    <h3 class="hackaton-title mb-0">HACKATON GenAI</h3>
                </div>
                <div class="col-md-3 text-end">
                    <span class="powered-by">Powered by AWS</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Hero Section -->
    <div class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-2 text-center mb-3 mb-lg-0">
                    <!-- Ignite Rocket Sticker with Glow -->
                    <div class="ignite-sticker-rocket">
                        <img src="data:image/png;base64,''' + get_base64_image('Class2025IgniteSticker.png') + '''" 
                             alt="Ignite Rocket Sticker" 
                             style="width: 150px; height: auto; max-width: 100%;">
                    </div>
                </div>
                <div class="col-lg-8">
                    <h1 class="display-4 fw-bold mb-3">
                        <i class="fas fa-trophy me-3"></i>
                        Ignite Innovative GenAI Training
                    </h1>
                    <p class="lead mb-4">Competition Voting System - DynamoDB Version</p>
                    <div class="d-flex gap-3">
                        <span class="badge bg-success fs-6">
                            <i class="fas fa-database me-1"></i>
                            Persistent Storage
                        </span>
                        <span class="badge bg-info fs-6">
                            <i class="fas fa-sync me-1"></i>
                            Real-time Updates
                        </span>
                        <span class="badge bg-warning text-dark fs-6">
                            <i class="fas fa-users me-1"></i>
                            AWS Brazil Oneteam
                        </span>
                        <span class="badge bg-primary fs-6">
                            <i class="fas fa-code me-1"></i>
                            FSI 3 Hackaton
                        </span>
                    </div>
                </div>
                <div class="col-lg-2 text-center">
                    <!-- Ignite Flame Sticker with Glow -->
                    <div class="ignite-sticker-flame">
                        <img src="data:image/png;base64,''' + get_base64_image('IgniteSticker.png') + '''" 
                             alt="Ignite Flame Sticker" 
                             style="width: 150px; height: auto; max-width: 100%;">
                    </div>
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
                                    <i class="fas fa-lightbulb me-1"></i>
                                    <strong>Tip:</strong> Each criterion has a different weight in the final scoring.
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
                            Competition Leaderboard
                        </h5>
                        <button class="btn btn-light btn-sm" onclick="loadLeaderboard()">
                            <i class="fas fa-sync me-1"></i>Refresh
                        </button>
                    </div>
                    <div class="card-body">
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
                                    <div class="card-header bg-primary text-white">
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
                                <li>Calculate each judge's percentage: (Yes votes / 7 criteria) × 100</li>
                                <li>Final team score = Average of all judge percentages</li>
                                <li>Example: Judge A: 71.4%, Judge B: 85.7% → Final: 78.6%</li>
                            </ul>
                        </div>
                        
                        <h6>Example Scoring</h6>
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>Judge</th>
                                    <th>Yes Votes</th>
                                    <th>Percentage</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Judge 1</td>
                                    <td>6/7 Yes</td>
                                    <td>85.7%</td>
                                </tr>
                                <tr>
                                    <td>Judge 2</td>
                                    <td>5/7 Yes</td>
                                    <td>71.4%</td>
                                </tr>
                                <tr>
                                    <td>Judge 3</td>
                                    <td>7/7 Yes</td>
                                    <td>100.0%</td>
                                </tr>
                                <tr class="table-success">
                                    <td><strong>Final Score</strong></td>
                                    <td><strong>18/21 Total</strong></td>
                                    <td><strong>85.7%</strong></td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <h5 class="mt-4">Deliverables Required from Teams</h5>
                        <ul>
                            <li>Customer problem statement (max 200 words)</li>
                            <li>Success criteria definition process documentation</li>
                            <li>Demo recording or live presentation (15-20 minutes)</li>
                            <li>AWS services architecture diagram for PoC</li>
                            <li>GenAI services integration plan</li>
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
                                        <label for="team-problem-statement" class="form-label">Customer Problem Statement</label>
                                        <textarea class="form-control" id="team-problem-statement" rows="3" placeholder="Describe the customer problem this team is addressing..."></textarea>
                                    </div>
                                    <div class="mb-3">
                                        <label for="team-success-criteria" class="form-label">Success Criteria</label>
                                        <textarea class="form-control" id="team-success-criteria" rows="3" placeholder="Define what success looks like for this solution..."></textarea>
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
                                        <input type="text" class="form-control" id="judge-role">
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
                                        <i class="fas fa-trash me-1"></i>Clear All Data
                                    </button>
                                </div>
                                <hr>
                                <small class="text-muted">
                                    <i class="fas fa-info-circle me-1"></i>
                                    Use "Refresh All Data" if the interface is not updating properly.
                                    Use "Clear All Data" to completely reset the system.
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
                
                <!-- Criteria Management Row -->
                <div class="row mt-4">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header bg-warning text-dark">
                                <h6 class="mb-0">
                                    <i class="fas fa-list-check me-2"></i>Criteria Management
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>Add New Criteria</h6>
                                        <form id="add-criteria-form">
                                            <div class="mb-3">
                                                <label for="criteria-name" class="form-label">Criteria Name *</label>
                                                <input type="text" class="form-control" id="criteria-name" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="criteria-weight" class="form-label">Weight (%) *</label>
                                                <input type="number" class="form-control" id="criteria-weight" min="1" max="100" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="criteria-description" class="form-label">Description</label>
                                                <textarea class="form-control" id="criteria-description" rows="2" placeholder="Question or description for this criteria"></textarea>
                                            </div>
                                            <button type="submit" class="btn btn-warning">
                                                <i class="fas fa-plus me-1"></i>Add Criteria
                                            </button>
                                        </form>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>Current Criteria</h6>
                                        <div id="criteria-list">
                                            <div class="text-center">
                                                <div class="spinner-border text-warning" role="status">
                                                    <span class="visually-hidden">Loading...</span>
                                                </div>
                                                <p class="mt-2">Loading criteria...</p>
                                            </div>
                                        </div>
                                        <button class="btn btn-outline-warning btn-sm mt-2" onclick="loadCriteriaList()">
                                            <i class="fas fa-sync me-1"></i>Refresh Criteria
                                        </button>
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
            
            const responseData = await response.json();
            
            if (!response.ok) {
                // For 409 (Conflict) status, include the response data in the error
                if (response.status === 409) {
                    const error = new Error('duplicate_votes');
                    error.response = responseData;
                    throw error;
                } else {
                    throw new Error(responseData.error || `HTTP error! status: ${response.status}`);
                }
            }
            
            return responseData;
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
                    
                    <!-- Team Details Section -->
                    <div id="team-details" class="mb-4" style="display: none;">
                        <div class="card border-info">
                            <div class="card-header bg-info text-white">
                                <h6 class="mb-0">
                                    <i class="fas fa-info-circle me-2"></i>
                                    Team Details
                                </h6>
                            </div>
                            <div class="card-body">
                                <div id="team-details-content"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <h6>Evaluation Criteria:</h6>
                        <div id="criteria-voting">
                            ${currentData.criteria.map(criteria => `
                                <div class="card mb-2">
                                    <div class="card-body">
                                        <div class="row align-items-center">
                                            <div class="col-md-6">
                                                <strong>${criteria.name}</strong>
                                                <small class="text-muted d-block">Weight: ${criteria.weight}%</small>
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
                                            <div class="col-md-2">
                                                <textarea class="form-control form-control-sm auto-expand-textarea" 
                                                         placeholder="Comments" 
                                                         id="comments_${criteria.id}"
                                                         rows="1"
                                                         style="resize: none; overflow: hidden; min-height: 31px;"></textarea>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="fas fa-vote-yea me-2"></i>Submit Votes
                        </button>
                    </div>
                </form>
            `;
            
            // Add team selection change handler
            document.getElementById('team-select').addEventListener('change', function() {
                const teamId = this.value;
                const teamDetailsDiv = document.getElementById('team-details');
                const teamDetailsContent = document.getElementById('team-details-content');
                
                if (teamId) {
                    const selectedTeam = currentData.teams.find(team => team.id === teamId);
                    if (selectedTeam) {
                        teamDetailsContent.innerHTML = `
                            <h5 class="text-primary mb-3">
                                <i class="fas fa-users me-2"></i>
                                ${selectedTeam.name}
                            </h5>
                            ${selectedTeam.problem_statement ? `
                                <div class="mb-3">
                                    <strong class="text-info">
                                        <i class="fas fa-question-circle me-1"></i>
                                        Customer Problem Statement:
                                    </strong>
                                    <p class="mt-1">${selectedTeam.problem_statement}</p>
                                </div>
                            ` : ''}
                            ${selectedTeam.success_criteria ? `
                                <div class="mb-3">
                                    <strong class="text-success">
                                        <i class="fas fa-bullseye me-1"></i>
                                        Success Criteria:
                                    </strong>
                                    <p class="mt-1">${selectedTeam.success_criteria}</p>
                                </div>
                            ` : ''}
                        `;
                        teamDetailsDiv.style.display = 'block';
                    }
                } else {
                    teamDetailsDiv.style.display = 'none';
                }
            });
            
            // Add form submission handler
            document.getElementById('voting-form').addEventListener('submit', handleVoteSubmission);
            
            // Add auto-expanding functionality to comment textareas
            const commentTextareas = document.querySelectorAll('.auto-expand-textarea');
            commentTextareas.forEach(textarea => {
                // Auto-expand function
                function autoExpand() {
                    textarea.style.height = 'auto';
                    textarea.style.height = Math.max(31, textarea.scrollHeight) + 'px';
                }
                
                // Add event listeners
                textarea.addEventListener('input', autoExpand);
                textarea.addEventListener('focus', autoExpand);
                
                // Set initial height
                autoExpand();
            });
        }
        
        // Handle vote submission
        async function handleVoteSubmission(event, overwriteExisting = false) {
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
                        
                        votes.push({
                            criteria_id: criteria.id,
                            score: parseInt(selectedValue.value),
                            comments: comments
                        });
                    }
                }
                
                if (votes.length === 0) {
                    alert('Please vote on at least one criterion.');
                    return;
                }
                
                // Use the new batch submission endpoint with email notification
                const response = await apiCall('/submit-votes', {
                    method: 'POST',
                    body: JSON.stringify({
                        judge_id: judgeId,
                        team_id: teamId,
                        votes: votes,
                        overwrite_existing: overwriteExisting
                    })
                });
                
                // Show success message with email confirmation
                const emailStatus = response.email_sent ? 
                    `\\n\\n📧 Confirmation email sent to: ${response.judge_email}` : 
                    '\\n\\n⚠️ Note: Email confirmation could not be sent.';
                
                let successMessage = `✅ Successfully submitted ${response.votes_count} votes!`;
                
                // Add overwrite information if applicable
                if (response.action === 'overwrite') {
                    successMessage += `\\n\\n🔄 Updated previous votes (${response.overwritten_votes} votes replaced)`;
                }
                
                alert(successMessage + emailStatus);
                
                // Reset form
                event.target.reset();
                
                // Reset textarea heights
                const commentTextareas = document.querySelectorAll('.auto-expand-textarea');
                commentTextareas.forEach(textarea => {
                    textarea.style.height = '31px';
                });
                
                // Hide team details section
                document.getElementById('team-details').style.display = 'none';
                
                // Refresh leaderboard if visible
                if (document.getElementById('leaderboard').classList.contains('show')) {
                    loadLeaderboard();
                }
                
            } catch (error) {
                console.error('Error submitting votes:', error);
                
                // Handle duplicate vote error specifically
                if (error.message.includes('duplicate_votes') || (error.response && error.response.error === 'duplicate_votes')) {
                    const errorData = error.response || JSON.parse(error.message);
                    const existingDate = new Date(errorData.existing_votes_date).toLocaleString();
                    
                    const confirmMessage = `⚠️ DUPLICATE VOTE DETECTED\\n\\n` +
                        `You have already voted for this team on ${existingDate}.\\n` +
                        `Existing votes: ${errorData.existing_votes_count}\\n\\n` +
                        `Do you want to OVERWRITE your previous votes?\\n\\n` +
                        `⚠️ This action cannot be undone!`;
                    
                    if (confirm(confirmMessage)) {
                        // Retry with overwrite flag
                        await handleVoteSubmission(event, true);
                        return;
                    } else {
                        alert('Vote submission cancelled. Your previous votes remain unchanged.');
                    }
                } else {
                    alert('Failed to submit votes: ' + error.message);
                }
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
                                        ${team.problem_statement ? `
                                            <div class="mb-2">
                                                <strong class="text-info">
                                                    <i class="fas fa-question-circle me-1"></i>
                                                    Customer Problem Statement:
                                                </strong>
                                                <p class="card-text mt-1">${team.problem_statement}</p>
                                            </div>
                                        ` : ''}
                                        ${team.success_criteria ? `
                                            <div class="mb-2">
                                                <strong class="text-success">
                                                    <i class="fas fa-bullseye me-1"></i>
                                                    Success Criteria:
                                                </strong>
                                                <p class="card-text mt-1">${team.success_criteria}</p>
                                            </div>
                                        ` : ''}
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
        
        // Load leaderboard
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
                                                <small class="text-muted">${team.problem_statement || 'No problem statement provided'}</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-success score-badge">
                                                    ${team.total_score.toFixed(1)}
                                                </div>
                                                <small class="d-block text-muted">Total Score</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-info score-badge">
                                                    ${team.vote_count}
                                                </div>
                                                <small class="d-block text-muted">Votes</small>
                                            </div>
                                            <div class="col-md-2 text-center">
                                                <div class="badge bg-primary score-badge">
                                                    ${team.judge_count}
                                                </div>
                                                <small class="d-block text-muted">Judges</small>
                                            </div>
                                            <div class="col-md-1 text-center">
                                                <div class="badge bg-secondary">
                                                    ${(team.weighted_percentage).toFixed(1)}%
                                                </div>
                                                <small class="d-block text-muted">Score</small>
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
            const problemStatement = document.getElementById('team-problem-statement').value.trim();
            const successCriteria = document.getElementById('team-success-criteria').value.trim();
            
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
                    body: JSON.stringify({ 
                        name, 
                        problem_statement: problemStatement,
                        success_criteria: successCriteria 
                    })
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
        
        // Add criteria
        document.getElementById('add-criteria-form').addEventListener('submit', async function(event) {
            event.preventDefault();
            
            const name = document.getElementById('criteria-name').value.trim();
            const weight = document.getElementById('criteria-weight').value;
            const description = document.getElementById('criteria-description').value.trim();
            
            if (!name || !weight) {
                alert('Criteria name and weight are required.');
                return;
            }
            
            const submitButton = event.target.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Adding...';
            submitButton.disabled = true;
            
            try {
                await apiCall('/criteria', {
                    method: 'POST',
                    body: JSON.stringify({ name, weight: parseInt(weight), description })
                });
                
                alert('Criteria added successfully!');
                event.target.reset();
                
                // Refresh data
                await loadInitialData();
                loadCriteriaList();
                
            } catch (error) {
                console.error('Error adding criteria:', error);
                alert('Failed to add criteria: ' + error.message);
            } finally {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        });
        
        // Load criteria list for management
        async function loadCriteriaList() {
            const container = document.getElementById('criteria-list');
            
            try {
                const criteria = await apiCall('/criteria');
                
                if (criteria.length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info small">
                            <i class="fas fa-info-circle me-1"></i>
                            No criteria found.
                        </div>
                    `;
                    return;
                }
                
                const totalWeight = criteria.reduce((sum, c) => sum + parseFloat(c.weight), 0);
                
                container.innerHTML = `
                    <div class="small mb-2">
                        <strong>Total Weight: ${totalWeight}%</strong>
                        ${totalWeight !== 100 ? '<span class="text-warning"> (Should be 100%)</span>' : '<span class="text-success"> ✓</span>'}
                    </div>
                    ${criteria.map(criteria => `
                        <div class="card mb-2">
                            <div class="card-body py-2">
                                <div class="row align-items-center">
                                    <div class="col-md-6">
                                        <strong>${criteria.name}</strong>
                                        <small class="d-block text-muted">${criteria.description || 'No description'}</small>
                                    </div>
                                    <div class="col-md-3">
                                        <span class="badge bg-primary">${criteria.weight}%</span>
                                    </div>
                                    <div class="col-md-3">
                                        <button class="btn btn-danger btn-sm" onclick="deleteCriteria('${criteria.id}', '${criteria.name}')">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                `;
                
            } catch (error) {
                console.error('Error loading criteria list:', error);
                container.innerHTML = `
                    <div class="alert alert-danger small">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        Failed to load criteria: ${error.message}
                    </div>
                `;
            }
        }
        
        // Delete criteria
        async function deleteCriteria(criteriaId, criteriaName) {
            if (!confirm(`Are you sure you want to delete "${criteriaName}"?\\n\\nThis will also delete all votes for this criteria.`)) {
                return;
            }
            
            try {
                const result = await apiCall(`/criteria/${criteriaId}`, {
                    method: 'DELETE'
                });
                
                alert(`Criteria "${criteriaName}" deleted successfully!\\nDeleted ${result.deleted_votes} related votes.`);
                
                // Refresh data
                await loadInitialData();
                loadCriteriaList();
                
            } catch (error) {
                console.error('Error deleting criteria:', error);
                alert('Failed to delete criteria: ' + error.message);
            }
        }
        
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
            if (!confirm('Are you sure you want to delete ALL teams, judges, and votes? This will completely reset the system.')) {
                return;
            }
            
            if (!confirm('This is your final warning. ALL DATA will be permanently deleted. Continue?')) {
                return;
            }
            
            try {
                const result = await apiCall('/clear-sample-data', {
                    method: 'POST'
                });
                
                console.log('All data cleared:', result);
                alert(`Success! Deleted ${result.deleted_teams} teams, ${result.deleted_judges} judges, and ${result.deleted_votes} votes.`);
                
                // Force refresh currentData from server
                console.log('Forcing refresh of currentData...');
                currentData = { teams: [], judges: [], criteria: currentData.criteria || [] };
                
                // Force reload all data from server
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
                    loadCriteriaList();
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
