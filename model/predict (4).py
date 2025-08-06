
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def load_model_and_features(model_path: str, features_path: str):
    model = joblib.load(model_path)
    with open(features_path, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    return model, feature_cols

def coerce_types_and_align(df: pd.DataFrame, feature_cols):
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].astype(str).str.lower()
            if s.isin(["true", "false"]).any():
                df.loc[s.eq("true"), col] = True
                df.loc[s.eq("false"), col] = False
                df[col] = df[col].astype("boolean").astype(bool)
            else:
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception:
                    pass
    for c in feature_cols:
        if c not in df.columns:
            df[c] = np.nan
    df = df[feature_cols]
    return df

def predict_from_dataframe(model, feature_cols, df_in: pd.DataFrame) -> pd.Series:
    df_prepped = coerce_types_and_align(df_in, feature_cols)
    preds = model.predict(df_prepped)
    return pd.Series(preds, index=df_in.index, name="prediction_price_usd")

def best_trade_route_for_product(model, feature_cols, base_input, countries_list):
    predictions = []
    for country in countries_list:
        sample = base_input.copy()
        sample["country"] = country
        df_sample = pd.DataFrame([sample])
        pred_price = predict_from_dataframe(model, feature_cols, df_sample).iloc[0]
        predictions.append({
            "country": country,
            "price_usd": round(float(pred_price), 2)
        })
    
   
    cheapest = min(predictions, key=lambda x: x["price_usd"])
    most_expensive = max(predictions, key=lambda x: x["price_usd"])
    profit = round(most_expensive["price_usd"] - cheapest["price_usd"], 2)

    return cheapest, most_expensive, profit, predictions


def parse_kv_pairs(kv_list):
    out = {}
    for kv in kv_list or []:
        if "=" not in kv:
            print(f"--kv 'key=value' biçiminde olmalı, sorunlu: {kv}", file=sys.stderr)
            sys.exit(2)
        k, v = kv.split("=", 1)
        k = k.strip()
        v = v.strip()
        if v.lower() in ("true", "false"):
            out[k] = (v.lower() == "true")
        else:
            try:
                out[k] = float(v) if "." in v else int(v)
            except Exception:
                out[k] = v
    return out

def predict_for_all_countries(model, feature_cols, base_input, countries_list):
    results = []
    for country in countries_list:
        sample = base_input.copy()
        sample['country'] = country
        df_sample = pd.DataFrame([sample])
        pred_price = predict_from_dataframe(model, feature_cols, df_sample).iloc[0]
        results.append({
            "country": country,
            "predicted_price_usd": round(float(pred_price), 2)
        })
    return results

def main():
    ap = argparse.ArgumentParser(description="E-ticaret fiyat tahmin modeli")
    ap.add_argument("--model_path", default="ecomm_price_model_rf.joblib", help="Joblib model yolu")
    ap.add_argument("--features_path", default="feature_columns.json", help="Özellik listesi JSON yolu")
    ap.add_argument("--kv", action="append", help='Tek örnek için key=value çiftleri')
    args = ap.parse_args()

    if not Path(args.model_path).exists():
        print(f"Model bulunamadı: {args.model_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.features_path).exists():
        print(f"Özellik listesi bulunamadı: {args.features_path}", file=sys.stderr)
        sys.exit(1)

    model, feature_cols = load_model_and_features(args.model_path, args.features_path)

    if args.kv:
        sample = parse_kv_pairs(args.kv)
        all_countries = ["USA", "Germany", "France","India","Turkey","China"]

        predictions = predict_for_all_countries(model, feature_cols, sample, all_countries)

      
        product_info = sample.get("category", "Bu ürün")
        response_lines = [f" {product_info} için tahmini fiyatlar:"]
        for pred in predictions:
            response_lines.append(f"  - {pred['country']}: {pred['predicted_price_usd']} USD")
        print("\n".join(response_lines))
        return

   
    print("Kullanım örneği:")
    print('python predict.py --kv "category=Electronics" --kv "brand=Sony" --kv "city=Berlin" --kv "shipping_cost=6.0" --kv "seller=DemoSeller" --kv "stock=True" --kv "platform=Amazon" --kv "month=7"')

if __name__ == "__main__":
    main()
