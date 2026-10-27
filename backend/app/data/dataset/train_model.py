import csv
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Generate synthetic representative dataset if dataset.csv doesn't exist
DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset.csv')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.joblib')

PHISHING_TEMPLATES = [
    "URGENT: Your {service} account will be suspended in 2 hours. Reset credential password immediately.",
    "Account Suspension Alert: Your {service} account will be suspended in 2 hours due to unverified login attempts.",
    "SECURITY ALERT: Unauthorized login attempt from {city}. Verify your account now at {url}.",
    "Failure to verify will result in immediate termination of email services and file access.",
    "Your {service} mailbox is full and will be suspended in 2 hours unless verified.",
    "Critical Security Notice: {service} credential reset required within 2 hours to avoid suspension.",
    "Immediate action required: Reset your credential password at {url} before cutoff time.",
    "Urgent: Unverified login detected. Your {service} account is scheduled for suspension in 2 hours.",
    "Security Team Warning: Account suspension pending in 2 hours due to policy violation.",
    "DocuSign: Executive document signature pending for wire approval.",
    "Wire transfer required immediately: ${amount} for confidential acquisition closing.",
    "Updated banking details for invoice #{inv} — please wire payment to our new bank account.",
    "Action Required: Update your payroll direct deposit account before cutoff time.",
    "Urgent gift card procurement: Please buy ${amount} in Apple gift cards for executive meeting.",
    "IRS Notification: Tax audit statement available. Click link to verify identity.",
    "Bank Transfer Notice: Unrecognized debit of ${amount}. Log in to cancel transaction."
]

LEGIT_TEMPLATES = [
    "Attached is the updated quarterly financial audit report review for your records.",
    "Meeting follow up and technical architecture design proposal for next sprint.",
    "Hi team, please see attached notes from today's engineering sync.",
    "Weekly status update: Sprint goals on track for release next Tuesday.",
    "Thanks for sending over the project timeline. I will review with leadership.",
    "Happy Friday everyone, reminder to submit your timecards by end of day.",
    "Documentation updated for the new authentication microservice API endpoints.",
    "Lunch and learn session scheduled for Thursday on vector embeddings.",
    "Please find attached the signed vendor agreement for software licenses.",
    "Thank you for attending the webinar on email security best practices."
]

SERVICES = ["Microsoft 365", "Google Workspace", "PayPal", "Chase Bank", "Salesforce", "AWS Console"]
CITIES = ["Bucharest", "Moscow", "Lagos", "Beijing", "Frankfurt", "Kyiv"]
URLS = ["http://micros0ft-support.net/reset", "http://secure-verify.cc/login", "http://banking-update.info"]

def generate_dataset():
    rows = []
    import random
    random.seed(42)
    
    # Generate 300 phishing / BEC samples
    for i in range(300):
        tmpl = random.choice(PHISHING_TEMPLATES)
        text = tmpl.format(
            service=random.choice(SERVICES),
            city=random.choice(CITIES),
            url=random.choice(URLS),
            amount=random.randint(1000, 95000),
            inv=random.randint(10000, 99999)
        )
        t_low = text.lower()
        if any(w in t_low for w in ["suspended", "login", "quota", "termination", "credential", "password", "reset", "security"]):
            label = "phishing"
        elif any(w in t_low for w in ["wire", "invoice", "banking", "gift card", "deposit"]):
            label = "bec_pattern"
        else:
            label = "suspicious"
        rows.append((text, label))
        
    # Generate 300 legitimate samples
    for i in range(300):
        tmpl = random.choice(LEGIT_TEMPLATES)
        rows.append((tmpl, "legitimate"))
        
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['text', 'label'])
        writer.writerows(rows)
    print(f"Generated dataset with {len(rows)} samples at {DATASET_PATH}")

def train():
    generate_dataset()
        
    texts, labels = [], []
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            texts.append(row['text'])
            labels.append(row['label'])
            
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english', ngram_range=(1, 2))),
        ('clf', LogisticRegression(C=1.0, max_iter=200))
    ])
    
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, test_size=0.2, random_state=42)
    pipeline.fit(X_train, y_train)
    
    print("Model Evaluation:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved trained classifier model to {MODEL_PATH}")

if __name__ == '__main__':
    train()
