import time
import joblib
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from google_play_scraper import reviews, Sort

# ==========================================
# 1. CONFIGURATION & DATABASE CONNECTION
# ==========================================
USER = "" #your sql server credentials here
PASSWORD = "" 
HOST = ""               
PORT = ""                    
DATABASE = "safaricom_analytics" 

DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(DATABASE_URL)

# Test the connection
with engine.connect() as connection:
    result = connection.execute(sqlalchemy.text("SELECT VERSION();"))
    version = result.fetchone()[0]
    print(f"✅ Success! Connected to MySQL Server version: {version}")

# ==========================================
# 2. DATA ACQUISITION (SCRAPING)
# ==========================================
def scrape_reviews(num_batches=50, count_per_batch=1000):
    print("⏳ Starting Play Store scraper...")
    all_reviews = []
    token = None  
    
    for i in range(num_batches):  
        batch, token = reviews(
            'com.safaricom.mpesa.lifestyle',
            lang='en',
            country='ke',
            sort=Sort.NEWEST,
            count=count_per_batch,
            continuation_token=token  
        )
        all_reviews.extend(batch)
        print(f"Batch {i+1} done — total so far: {len(all_reviews)}")
        time.sleep(2)  
        
    return pd.DataFrame(all_reviews)

# ==========================================
# 3. DATA TRANSFORMATION (CLEANING)
# ==========================================
def transform_review_data(raw_df):
    print("⏳ Starting data transformation and cleaning protocols...")
    columns_to_keep = ['reviewId', 'userName', 'content', 'score', 'at']
    df = raw_df[columns_to_keep].copy()
    
    df = df.rename(columns={
        'reviewId': 'review_id',
        'userName': 'user_name',
        'content': 'clean_text',
        'score': 'rating',
        'at': 'posted_at'
    })
    
    df = df.dropna(subset=['clean_text'])
    df['clean_text'] = df['clean_text'].astype(str).str.replace(r'http\S+|www.\S+', '', regex=True)
    df['clean_text'] = df['clean_text'].str.replace(r'#', '', regex=True)
    df['clean_text'] = df['clean_text'].str.replace(r'[^\w\s,.\!?]', '', regex=True)
    df['clean_text'] = df['clean_text'].str.strip().str.lower()
    df = df[df['clean_text'] != ""]
    
    print(f"Transformation complete! Cleaned dataset shape: {df.shape}")
    return df

# ==========================================
# 4. DATABASE LOADING
# ==========================================
def load_to_database(df, connection_engine):
    print(f"⏳ Transporting {df.shape[0]} clean rows to MySQL...")
    try:
        with connection_engine.connect() as connection:
            with connection.begin():
                df.to_sql(
                    name='app_reviews',
                    con=connection,
                    if_exists='append',
                    index=False
                )
        print("🚀 Success! Transaction committed directly to the database.")
    except Exception as e:
        print(f"❌ Database load failed! Error Details: {e}")

# ==========================================
# 5. ML INFERENCE
# ==========================================
def run_inference_and_save(df, connection_engine):
    print("⏳ Loading machine learning assets...")
    # This is the line that was crashing due to SciPy
    tfidf = joblib.load(r"C:\Users\HP\Downloads\vectorizer.pkl")
    model = joblib.load(r"C:\Users\HP\Downloads\sentiment_model.pkl")
    
    print("⏳ Vectorizing text and predicting sentiment...")
    X_tfidf = tfidf.transform(df['clean_text'])
    df['sentiment_encoded'] = model.predict(X_tfidf)
    
    label_map = {0: 'Negative', 1: 'Positive'}
    df['sentiment'] = df['sentiment_encoded'].map(label_map)
    
    print("⏳ Saving final predictions back to MySQL...")
    try:
        with connection_engine.connect() as connection:
            with connection.begin():
                df.to_sql(
                    name='predicted_reviews',
                    con=connection,
                    if_exists='append',
                    index=False
                )
        print("🎉 PIPELINE COMPLETE! True binary predictions pushed to 'predicted_reviews'.")
    except Exception as e:
        print(f"Inference save failed: {e}")
    return df

# ==========================================
# 6. EXECUTION PIPELINE
# ==========================================
if __name__ == "__main__":
    # --- STEP A: Fetch and Clean Data ---
    raw_data = scrape_reviews(num_batches=50, count_per_batch=1000)
    cleaned_df = transform_review_data(raw_data)
    
    # --- STEP B: Load raw features to DB ---
    load_to_database(cleaned_df, engine)
    
    # --- STEP C: Predict and Save ML Output ---
    final_df = run_inference_and_save(cleaned_df, engine)
    
    # --- QUICK METRICS ---
    print("\n📊 Sentiment Distribution Summary:")
    print(final_df['sentiment'].value_counts())

# In[ ]:




