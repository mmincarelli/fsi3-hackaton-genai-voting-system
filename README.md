# FSI 3 Hackaton GenAI Voting System

A serverless voting system built for the FSI 3 Hackaton GenAI Training competition, featuring real-time voting, email notifications, and comprehensive team management.

![Architecture](docs/architecture-overview.png)

## 🏆 Features

### 🎯 **Core Functionality**
- **Team Management**: Problem statements, success criteria, and team details
- **Judge Administration**: Email-based judge management with role assignments
- **Real-time Voting**: Interactive voting interface with auto-expanding comments
- **Live Leaderboard**: Dynamic scoring with percentage calculations
- **Email Notifications**: Professional HTML email confirmations via Amazon SES

### 🔒 **Security & Business Rules**
- **Duplicate Vote Prevention**: Warns judges and allows vote updates with confirmation
- **AWS Shield Standard**: Automatic DDoS protection
- **IAM Role-Based Access**: No secrets stored, temporary credentials only
- **HTTPS Enforcement**: TLS encryption with security headers
- **Private Lambda Execution**: No direct internet access

### 🎨 **User Experience**
- **Mobile Responsive**: Bootstrap 5 with optimized mobile layout
- **Auto-expanding Comments**: Textarea grows as judges type detailed feedback
- **Professional Branding**: AWS Brazil Oneteam logo and FSI 3 Hackaton styling
- **Animated Elements**: F1-inspired trophy with AWS Bedrock branding
- **Ignite Stickers**: Equalized Class 2025 rocket and flame stickers

## 🏗️ Architecture

### **Serverless AWS Stack**
- **API Gateway**: REST API with HTTPS enforcement
- **AWS Lambda**: Python 3.9 business logic
- **DynamoDB**: 5 tables for teams, judges, votes, criteria, and settings
- **Amazon SES**: DMARC-compliant email notifications
- **S3**: Static assets and Ignite stickers storage
- **CloudFormation/SAM**: Infrastructure as Code

### **Security Architecture**
```
Internet → AWS Shield → API Gateway → Lambda (Private) → IAM Role → AWS Services
```

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.9+

### Deployment
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fsi3-hackaton-genai-voting-system.git
cd fsi3-hackaton-genai-voting-system

# Build the application
sam build

# Deploy to AWS
sam deploy --guided

# Follow the prompts to configure:
# - Stack name: genai-voting-system
# - AWS Region: us-east-1 (or your preferred region)
# - Confirm changes before deploy: Y
# - Allow SAM to create IAM roles: Y
```

### Post-Deployment Setup
1. **Verify SES Email**: Add your sender email to Amazon SES
2. **Upload Stickers**: Add Ignite sticker images to the created S3 bucket
3. **Initialize Data**: Use the admin interface to add teams, judges, and criteria

## 📊 Usage

### **For Judges**
1. Access the voting interface
2. Select your name from the judge dropdown
3. Choose a team to evaluate
4. Vote Yes/No on each criterion with optional comments
5. Submit votes (email confirmation will be sent)

### **For Administrators**
1. Use the Admin tab to manage:
   - Teams (add problem statements and success criteria)
   - Judges (add email addresses and roles)
   - Criteria (define evaluation parameters)
2. Monitor the leaderboard for real-time results
3. View documentation for complete scoring methodology

## 🔧 Configuration

### **Environment Variables**
The system uses these DynamoDB table references:
- `TEAMS_TABLE`: Team information and problem statements
- `JUDGES_TABLE`: Judge details and email addresses
- `VOTES_TABLE`: Voting records with duplicate prevention
- `CRITERIA_TABLE`: Evaluation criteria and weights
- `SETTINGS_TABLE`: System configuration

### **Email Configuration**
Update the sender email in `app_dynamodb.py`:
```python
# Line ~145: Update with your verified SES email
Source='your-verified-email@domain.com'
```

## 📈 Monitoring

### **CloudWatch Metrics**
- API Gateway request/error rates
- Lambda execution duration and errors
- DynamoDB read/write capacity
- SES email delivery status

### **Security Monitoring**
- Failed authentication attempts
- Rate limit violations
- Suspicious request patterns

## 💰 Cost Estimation

### **Typical Hackathon Usage** (50 judges, 10 teams, 7 criteria)
- **Lambda**: ~$0.20/month
- **DynamoDB**: ~$2-5/month
- **API Gateway**: ~$3.50/month
- **SES**: ~$0.10/month
- **S3**: ~$0.50/month
- **Total**: ~$6-10/month

### **Enhanced Security** (Optional)
- **AWS WAF v2**: +$5/month + $0.60/million requests
- **Shield Advanced**: $3,000/month (enterprise only)

## 🛡️ Security Features

### **Current Protection**
- ✅ **AWS Shield Standard**: Automatic DDoS protection
- ✅ **HTTPS Only**: TLS 1.2+ encryption
- ✅ **IAM Roles**: No secrets management required
- ✅ **Private Lambda**: No direct internet access
- ✅ **Security Headers**: XSS, CSRF, and clickjacking protection

### **Optional Enhancements**
- 🔒 **AWS WAF v2**: Application-layer firewall (template included)
- 🔒 **Rate Limiting**: Advanced per-IP throttling
- 🔒 **Geo-blocking**: Country-based access control

## 📁 Project Structure

```
├── app_dynamodb.py          # Main Lambda function
├── template.yaml            # SAM CloudFormation template
├── template-with-waf.yaml   # Enhanced template with WAF
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── docs/                   # Documentation and diagrams
│   ├── architecture-overview.png
│   ├── security-flow.png
│   └── user-guide.md
├── assets/                 # Static assets
│   ├── Class2025IgniteSticker.png
│   └── IgniteSticker.png
└── .gitignore             # Git ignore file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AWS Brazil Oneteam** for the professional logo and branding
- **FSI 3 Hackaton GenAI Training** for the competition framework
- **Amazon Ignite Program** for the sticker assets
- **AWS Community** for serverless best practices

## 📞 Support

For questions or support:
- Create an issue in this repository
- Contact the development team
- Check the [documentation](docs/user-guide.md)

---

**Built with ❤️ using AWS Serverless Technologies**

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=for-the-badge&logo=amazon-dynamodb&logoColor=white)
![Lambda](https://img.shields.io/badge/Lambda-FF9900?style=for-the-badge&logo=aws-lambda&logoColor=white)
