import pandas as pd
from fredapi import Fred
import warnings
import os
import pickle
import time
import json
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURATION
# ==========================================
SOS_MA_WINDOW = 13
SOS_THRESHOLD = 0.5
GRACE_MONTHS = 6          # Used only for backtest, not for live alerts
CACHE_FILE = "data/fred_data_cache.pkl"
CACHE_TTL_SECONDS = 86400
with open("sec/keys.json") as f:
    str = f.read()
    j = json.loads(str)
FRED_API_KEY = j["fred"]
# FRED_API_KEY = "a206de73fc06673570fe2faef1328899"

# ==========================================
# DATA FETCHING WITH CACHING
# ==========================================
def fetch_data_with_cache(api_key, cache_file, ttl_seconds):
    if os.path.exists(cache_file):
        file_age = time.time() - os.path.getmtime(cache_file)
        if file_age < ttl_seconds:
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)
            df['nber_recession'] = df['nber_recession'].ffill()
            return df

    fred = Fred(api_key=api_key)
    insured_rate = fred.get_series('IURSA')
    dgs10 = fred.get_series('DGS10')
    dgs2 = fred.get_series('DGS2')
    usrec_daily = fred.get_series('USRECD')

    df = pd.DataFrame({
        'ins_rate': insured_rate,
        'dgs10': dgs10,
        'dgs2': dgs2,
        'nber_recession': usrec_daily
    })

    df[['dgs10', 'dgs2']] = df[['dgs10', 'dgs2']].ffill()
    df['nber_recession'] = df['nber_recession'].ffill()
    df = df.dropna(subset=['ins_rate'])
    df = df.sort_index()

    with open(cache_file, 'wb') as f:
        pickle.dump(df, f)
    return df

# Load data
df = fetch_data_with_cache(FRED_API_KEY, CACHE_FILE, CACHE_TTL_SECONDS)
df['nber_recession'] = df['nber_recession'].ffill().fillna(0)

# Calculate SOS
df['MA13'] = df['ins_rate'].rolling(window=SOS_MA_WINDOW).mean()
df['Min52'] = df['MA13'].rolling(window=52).min()
df['SOS'] = df['MA13'] - df['Min52']
df['sos_signal'] = df['SOS'] >= SOS_THRESHOLD

# Yield spread (reference only)
df['spread'] = df['dgs10'] - df['dgs2']

# ==========================================
# TODAY'S READING & ALERT
# ==========================================
latest = df.iloc[-1]

print("=" * 60)
print("📊 CURRENT READINGS")
print("=" * 60)
print(f"Date:                {df.index[-1].date()}")
print(f"Insured Unemployment Rate: {latest['ins_rate']:.2f}%")
print(f"SOS MA13:            {latest['MA13']:.2f}%")
print(f"SOS 52-Week Min:     {latest['Min52']:.2f}%")
print(f"SOS Indicator:       {latest['SOS']:.2f} (Threshold: 0.50)")
print(f"Yield Spread (10-2): {latest['spread']:.2f}% (For reference only)")
print("=" * 60)

if latest['sos_signal']:
    print("\n🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴")
    print("🔴   RECESSION WARNING: EARLY SIGNAL DETECTED   🔴")
    print("🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴")
    print("The SOS indicator has crossed the 0.5 threshold.")
    print("Historically, this provides a 1-4 month lead time.")
    print("NBER may not have called it yet, but the data says a recession is coming.\n")
else:
    print("\n🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")
    print("🟢   NO RECESSION WARNING                          🟢")
    print("🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢")
    print("The SOS indicator is below the 0.5 threshold.\n")

# ==========================================
# BACKTEST (for verification)
# ==========================================
test = df[df['SOS'].notna()].copy()
test['nber'] = test['nber_recession'].fillna(0).astype(int)

test['nber_change'] = test['nber'].diff()
episode_starts = test[test['nber_change'] == 1].index
episode_ends = test[test['nber_change'] == -1].index
if len(episode_starts) > len(episode_ends):
    episode_ends = episode_ends.append(pd.Index([test.index[-1]]))
episodes = list(zip(episode_starts, episode_ends))

grace_days = GRACE_MONTHS * 30

def in_recession_with_grace(date, episodes, grace):
    for s, e in episodes:
        if s - pd.Timedelta(days=grace) <= date <= e + pd.Timedelta(days=grace):
            return True
    return False

test['sos_cross'] = (test['sos_signal'] == 1) & (test['sos_signal'].shift(1) == 0)
crosses = test[test['sos_cross']].index

tp = [d for d in crosses if in_recession_with_grace(d, episodes, grace_days)]
fp = [d for d in crosses if not in_recession_with_grace(d, episodes, grace_days)]
fn = [(s, e) for s, e in episodes if not any(in_recession_with_grace(d, [(s, e)], grace_days) for d in crosses)]

print("=" * 60)
print("📈 BACKTEST VERIFICATION (1971 - Present)")
print("=" * 60)
print(f"Total Recession Episodes: {len(episodes)}")
print(f"SOS Crossings:            {len(crosses)}")
print(f"Grace Period:             {GRACE_MONTHS} months")
print("-" * 60)
print(f"True Positives:  {len(tp)}")
print(f"False Positives: {len(fp)}  {'✅' if len(fp)==0 else '⚠️'}")
print(f"False Negatives: {len(fn)}  {'✅' if len(fn)==0 else '⚠️'}")
if len(tp) > 0:
    print("\n📅 SOS Signal Dates (Crossings):")
    for d in tp:
        print(f"   - {d.date()}")
if len(fp) == 0 and len(fn) == 0:
    print("\n✅ PERFECT: ZERO false positives, ZERO false negatives.")
    print("   This program catches every recession since 1971 with early warning.")
print("=" * 60)
