import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)

class HateSpeechDetector:
    def __init__(self, use_spell_check=True):
        self.vectorizer = None
        self.model = None
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.use_spell_check = use_spell_check
        
    def correct_spelling(self, text):
        try:
            corrected = str(TextBlob(text).correct())
            return corrected
        except:
            return text
    
    def preprocess_text(self, text):
        if pd.isna(text):
            return ""
        text = str(text)
        text = text.lower()
        
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)
        text = re.sub(r'@\w+|#\w+', '', text)
        
        text = re.sub(r'(\w)\1{2,}', r'\1\1', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        if self.use_spell_check:
            text = self.correct_spelling(text)
        
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        words = text.split()
        words = [self.lemmatizer.lemmatize(word) for word in words 
                 if word not in self.stop_words and len(word) > 2]
        
        return ' '.join(words)
    
    def prepare_features(self, texts, fit=False):
        if fit:
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            features = self.vectorizer.fit_transform(texts)
        else:
            features = self.vectorizer.transform(texts)
        return features
    
    def train(self, X_train, y_train, model_type='logistic'):
        models = {
            'logistic': LogisticRegression(max_iter=1000, random_state=42),
            'naive_bayes': MultinomialNB(),
        }
        
        self.model = models.get(model_type, models['logistic'])
        self.model.fit(X_train, y_train)
        
    def predict(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        
        processed_texts = [self.preprocess_text(text) for text in texts]
        features = self.prepare_features(processed_texts, fit=False)
        predictions = self.model.predict(features)
        probabilities = self.model.predict_probability(features) if hasattr(self.model, 'predict_probability') else None
        
        return predictions, probabilities
    
    def evaluate(self, X_test, y_test):
        predictions = self.model.predict(X_test)
        
        print("Model Evaluation:")
        print("=" * 50)
        print(f"Accuracy: {accuracy_score(y_test, predictions):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, predictions, 
                                   target_names=['Normal', 'Hate Speech']))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, predictions))


def load_dataset(csv_path):
    print(f"Loading dataset from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
        print(f"Dataset loaded successfully!")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        column_mapping = {}
        
        if 'Content' in df.columns:
            column_mapping['Content'] = 'content'
        elif 'text' in df.columns:
            column_mapping['text'] = 'content'
        elif 'Text' in df.columns:
            column_mapping['Text'] = 'content'
        
        if 'Label' in df.columns:
            column_mapping['Label'] = 'labels'
        elif 'is_offensive' in df.columns:
            column_mapping['is_offensive'] = 'labels'
        elif 'label' in df.columns:
            column_mapping['label'] = 'labels'
        elif 'hate_speech' in df.columns:
            column_mapping['hate_speech'] = 'labels'
        
        df = df.rename(columns=column_mapping)
        
        if 'content' not in df.columns or 'labels' not in df.columns:
            raise ValueError(f"CSV must contain text and label columns. Found: {df.columns.tolist()}")
        
        df = df[['content', 'labels']]
        
        df = df[df['labels'] != 'Label']
        df = df[df['labels'] != 'is_offensive']
        print(f"Removed header rows from data (if any)")
        
        df['labels'] = pd.to_numeric(df['labels'], errors='coerce')
        print(f"\nLabel distribution:")
        print(df['labels'].value_counts())
        df = df.dropna(subset=['content', 'labels'])
        print(f"\nShape after removing missing values: {df.shape}")
        
        return df
    
    except FileNotFoundError:
        print(f"Error: File not found at {csv_path}")
        print("Please ensure the CSV file exists at the specified path.")
        raise
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        raise


def combine_datasets(csv_paths):
    print("=" * 50)
    print("LOADING MULTIPLE DATASETS")
    print("=" * 50)
    
    all_datasets = []
    
    for i, csv_path in enumerate(csv_paths, 1):
        print(f"\n[Dataset {i}]")
        try:
            df = load_dataset(csv_path)
            all_datasets.append(df)
        except Exception as e:
            print(f"Warning: Could not load {csv_path}: {str(e)}")
            print("Continuing with other datasets...\n")
            continue
    
    if not all_datasets:
        raise ValueError("No datasets were successfully loaded!")
    
    combined_df = pd.concat(all_datasets, ignore_index=True)
    
    print("\n" + "=" * 50)
    print("COMBINED DATASET SUMMARY")
    print("=" * 50)
    print(f"Total samples: {len(combined_df)}")
    print(f"\nCombined label distribution:")
    print(combined_df['labels'].value_counts())
    print(f"\nLabel percentages:")
    print(combined_df['labels'].value_counts(normalize=True) * 100)
    
    original_size = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=['content'], keep='first')
    duplicates_removed = original_size - len(combined_df)
    print(f"\nRemoved {duplicates_removed} duplicate entries")
    print(f"Final dataset size: {len(combined_df)}")
    
    return combined_df

if __name__ == "__main__":
    CSV_FILE_PATHS = [
        "HateSpeechDataset.csv",
        "English_profanity_words.csv",
    ]
    
    df = combine_datasets(CSV_FILE_PATHS)
    detector = HateSpeechDetector(use_spell_check=True)
    
    print("\n" + "=" * 50)
    print("SPELL CORRECTION EXAMPLES:")
    print("=" * 50)
    test_misspellings = [
        "I haate thos poeple",
        "They are stoopid and dum fakfakfak",
        "Evryone desrves respct, Fakhar"
    ]
    for text in test_misspellings:
        corrected = detector.correct_spelling(text)
        print(f"Original:  {text}")
        print(f"Corrected: {corrected}\n")
    
    print("Preprocessing texts with spell correction...")
    df['processed_text'] = df['content'].apply(detector.preprocess_text)
    df = df[df['processed_text'].str.len() > 0]
    print(f"Shape after removing empty texts: {df.shape}")
    
    print("\nSplitting data into train and test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        df['processed_text'], df['labels'], 
        test_size=0.2, 
        random_state=42,
        stratify=df['labels']
    )
    
    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    
    print("\nExtracting features...")
    X_train_features = detector.prepare_features(X_train, fit=True)
    X_test_features = detector.prepare_features(X_test, fit=False)
    
    print("\nTraining and comparing models...")
    print("=" * 50)
    
    model_results = {}
    
    for model_name in ['logistic', 'naive_bayes']:
        print(f"\n{model_name.upper().replace('_', ' ')} MODEL:")
        detector.train(X_train_features, y_train, model_type=model_name)
        
        predictions = detector.model.predict(X_test_features)
        accuracy = accuracy_score(y_test, predictions)
        model_results[model_name] = accuracy
        
        detector.evaluate(X_test_features, y_test)
    
    print("\n" + "=" * 50)
    print("MODEL COMPARISON SUMMARY:")
    print("=" * 50)
    for model, acc in sorted(model_results.items(), key=lambda x: x[1], reverse=True):
        print(f"{model.upper().replace('_', ' ')}: {acc:.4f}")
    
    best_model = max(model_results, key=model_results.get)
    print(f"\nBest performing model: {best_model.upper().replace('_', ' ')}")
    
    print("\n" + "=" * 50)
    print("Testing with new examples:")
    print("=" * 50)
    
    test_texts = [
        "I really enjoy learning new things every day",
        "Those people are disgusting and should be removed",
        "Let's celebrate our differences and unite as one"
    ]
    detector.train(X_train_features, y_train, model_type=best_model)
    
    predictions, probabilities = detector.predict(test_texts)
    
    for i, text in enumerate(test_texts):
        label = "HATE SPEECH" if predictions[i] == 1 else "NORMAL"
        prob = probabilities[i][1] if probabilities is not None else 0
        print(f"\nText: {text}")
        print(f"Prediction: {label}")
        if probabilities is not None:
            print(f"Hate Speech Probability: {prob:.4f}")

