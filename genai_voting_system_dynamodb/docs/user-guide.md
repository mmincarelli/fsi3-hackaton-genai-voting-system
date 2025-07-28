# FSI 3 Hackaton GenAI Voting System - User Guide

## 🎯 Overview

This guide covers how to use the FSI 3 Hackaton GenAI voting system for judges, administrators, and system operators.

## 👨‍⚖️ For Judges

### Accessing the System
1. Navigate to the provided voting system URL
2. The system loads with the main voting interface

### Casting Votes
1. **Select Judge**: Choose your name from the "Select Judge" dropdown
2. **Select Team**: Choose the team you want to evaluate
3. **Review Team Details**: 
   - Problem statement will be displayed
   - Success criteria will be shown
   - Team description and additional details
4. **Vote on Criteria**: For each evaluation criterion:
   - Select **Yes** or **No**
   - Add optional comments in the expandable text area
   - Comments field grows automatically as you type
5. **Submit Votes**: Click "Submit Votes" button
6. **Email Confirmation**: You'll receive an email confirmation with your vote summary

### Duplicate Vote Handling
- If you try to vote for the same team twice, you'll see a warning
- The system shows when you previously voted and how many votes you submitted
- You can choose to:
  - **Cancel**: Keep your original votes
  - **Overwrite**: Replace your previous votes with new ones
- Overwriting is permanent and cannot be undone

### Comments Best Practices
- Use the auto-expanding comments field for detailed feedback
- Provide constructive criticism and suggestions
- Mention specific strengths and areas for improvement
- Comments are included in email confirmations and visible to administrators

## 👨‍💼 For Administrators

### Team Management
1. Go to the **Admin** tab
2. Click **Teams** sub-tab
3. **Add New Team**:
   - Enter team name
   - Add problem statement (detailed description of the challenge)
   - Define success criteria (what constitutes a successful solution)
   - Provide team description
4. **View Teams**: All teams are listed with their details

### Judge Management
1. In the **Admin** tab, click **Judges** sub-tab
2. **Add New Judge**:
   - Enter judge name
   - Add email address (must be valid for notifications)
   - Specify role (e.g., "Senior Technical Judge", "Business Judge")
3. **Email Requirements**: 
   - Judges must have valid email addresses
   - Email confirmations are sent after each vote submission

### Criteria Management
1. In the **Admin** tab, click **Criteria** sub-tab
2. **Add New Criteria**:
   - Enter criteria name (e.g., "Technical Innovation")
   - Set weight (1-10, affects scoring calculations)
   - Add description explaining what judges should evaluate
3. **Remove Criteria**: 
   - Click delete button next to any criteria
   - Warning: This will delete ALL votes for that criteria
   - Confirmation required before deletion

### Monitoring Results
1. **Leaderboard Tab**: View real-time results
   - Teams ranked by total score
   - Score breakdown by criteria
   - Judge participation statistics
2. **Documentation Tab**: Review scoring methodology and rules

## 🔧 For System Operators

### Deployment
```bash
# Initial deployment
sam build
sam deploy --guided

# Updates
sam build
sam deploy
```

### Email Configuration
1. **Verify SES Email**: 
   - Go to Amazon SES console
   - Verify the sender email address
   - Update `app_dynamodb.py` with verified email
2. **DMARC Setup** (optional):
   - Configure DNS records for your domain
   - Add SPF, DKIM, and DMARC records

### Monitoring
1. **CloudWatch Logs**: Monitor Lambda function execution
2. **API Gateway Metrics**: Track request volume and errors
3. **DynamoDB Metrics**: Monitor read/write capacity
4. **SES Metrics**: Track email delivery rates

### Troubleshooting

#### Common Issues

**Email Not Sending**
- Check SES email verification status
- Verify IAM permissions for SES
- Check CloudWatch logs for error messages

**Votes Not Saving**
- Check DynamoDB table permissions
- Verify table names in environment variables
- Review Lambda function logs

**Duplicate Vote Errors**
- Check judge-index on votes table
- Verify judge and team IDs are correct
- Review vote submission logic in logs

**Performance Issues**
- Monitor Lambda cold starts
- Check DynamoDB throttling
- Review API Gateway timeout settings

#### Log Analysis
```bash
# View Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/genai-voting"

# Get recent errors
aws logs filter-log-events --log-group-name "/aws/lambda/genai-voting-function" --filter-pattern "ERROR"
```

### Security Best Practices
1. **Regular Updates**: Keep dependencies updated
2. **Monitor Access**: Review CloudTrail logs
3. **Rate Limiting**: Consider enabling WAF for production
4. **Data Backup**: Enable DynamoDB point-in-time recovery

## 📊 Scoring Methodology

### Vote Calculation
1. **Individual Votes**: Yes = 1 point, No = 0 points
2. **Judge Percentage**: (Yes votes / Total criteria) × 100
3. **Team Score**: Average of all judge percentages
4. **Ranking**: Teams sorted by total score descending

### Example Calculation
**Team A evaluated by 2 judges on 7 criteria:**
- Judge 1: 5 Yes votes = 71.4%
- Judge 2: 6 Yes votes = 85.7%
- **Final Score**: (71.4% + 85.7%) ÷ 2 = 78.6%

## 🎨 Visual Features

### Branding Elements
- **AWS Brazil Oneteam Logo**: Professional header branding
- **FSI 3 Hackaton Banner**: Full-width competition branding
- **Ignite Stickers**: Class 2025 rocket and flame stickers
- **Animated Trophy**: F1-inspired trophy with AWS Bedrock elements

### Responsive Design
- **Desktop**: Full-featured interface with all elements
- **Tablet**: Optimized layout with adjusted spacing
- **Mobile**: Compact design with stacked elements

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: ARIA labels and semantic HTML
- **Color Contrast**: WCAG compliant color schemes
- **Font Scaling**: Responsive text sizing

## 📞 Support

### Getting Help
1. **Check Documentation**: Review this guide and README
2. **System Status**: Check the system status in the admin panel
3. **Error Messages**: Note exact error messages for troubleshooting
4. **Contact Support**: Reach out to the development team with:
   - Exact steps to reproduce the issue
   - Screenshots if applicable
   - Browser and device information

### Feedback
- Report bugs through the GitHub issue tracker
- Suggest improvements via pull requests
- Share usage feedback with the development team

---

**Last Updated**: July 28, 2025  
**Version**: 2.0  
**System URL**: https://rs1cc952n4.execute-api.us-east-1.amazonaws.com/Prod/
