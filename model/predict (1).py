
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

def load_model_and_features(model_path: str, features_path: str):
    """Model (.joblib) ve özellik listesi (.json) yükle"""
    model = joblib.load(model_path)
    with open(features_path, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    return model, feature_cols

def coerce_types_and_align(df: pd.DataFrame, feature_cols):
    """Tipleri dönüştür, eksik kolonları ekle, sıralamayı hizala"""
    df = df.copy()

    # True/False string -> bool
    for col in df.columns:
        if df[col].dtype == object:
            s = df[col].astype(str).str.lower()
            if s.isin(["true", "false"]).any():
                df.loc[s.eq("true"), col] = True
                df.loc[s.eq("false"), col] = False
                df[col] = df[col].astype("boolean").astype(bool)
            else:
                # Sayıya çevrilebilenleri çevir
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception:
                    pass

    # Eksik kolonları ekle
    for c in feature_cols:
        if c not in df.columns:
            df[c] = np.nan

    # Kolon sırasını hizala
    df = df[feature_cols]
    return df

def predict_from_dataframe(model, feature_cols, df_in: pd.DataFrame) -> pd.Series:
    """DataFrame içindeki satırlar için tahmin yap"""
    df_prepped = coerce_types_and_align(df_in, feature_cols)
    preds = model.predict(df_prepped)
    return pd.Series(preds, index=df_in.index, name="prediction_price_usd")

def parse_kv_pairs(kv_list):
    """--kv 'key=value' argümanlarını dict'e çevir"""
    out = {}
    for kv in kv_list or []:
        if "=" not in kv:
            print(f"--kv 'key=value' biçiminde olmalı, sorunlu: {kv}", file=sys.stderr)
            sys.exit(2)
        k, v = kv.split("=", 1)
        k = k.strip()
        v = v.strip()
        # tip kestirimi
        if v.lower() in ("true", "false"):
            out[k] = (v.lower() == "true")
        else:
            try:
                out[k] = float(v) if "." in v else int(v)
            except Exception:
                out[k] = v
    return out

def main():
    ap = argparse.ArgumentParser(description="E-ticaret fiyat tahmin modeli için predict scripti")
    ap.add_argument("--model_path", default="ecomm_price_model_rf.joblib", help="Joblib model yolu")
    ap.add_argument("--features_path", default="feature_columns.json", help="Özellik listesi JSON yolu")
    ap.add_argument("--input_csv", help="Girdi CSV dosyası (çoklu satır)")
    ap.add_argument("--output_csv", help="Çıktı CSV yolu (input_csv ile birlikte)")
    ap.add_argument("--input_json", help="Tek kayıt (dict) veya çoklu (list) JSON dosyası")
    ap.add_argument("--kv", action="append", help='Tek örnek için key=value çiftleri')
    args = ap.parse_args()

    # Model ve özellik listesi yükle
    if not Path(args.model_path).exists():
        print(f"Model bulunamadı: {args.model_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.features_path).exists():
        print(f"Özellik listesi bulunamadı: {args.features_path}", file=sys.stderr)
        sys.exit(1)

    model, feature_cols = load_model_and_features(args.model_path, args.features_path)

    # 1) CSV modu
    if args.input_csv:
        if not Path(args.input_csv).exists():
            print(f"CSV bulunamadı: {args.input_csv}", file=sys.stderr)
            sys.exit(1)
        df_in = pd.read_csv(args.input_csv)
        preds = predict_from_dataframe(model, feature_cols, df_in)
        df_out = df_in.copy()
        df_out["prediction_price_usd"] = preds
        if args.output_csv:
            df_out.to_csv(args.output_csv, index=False)
            print(f"Kaydedildi -> {args.output_csv}")
        else:
            print(df_out.to_csv(index=False))
        return

    # 2) JSON modu
    if args.input_json:
        if not Path(args.input_json).exists():
            print(f"JSON bulunamadı: {args.input_json}", file=sys.stderr)
            sys.exit(1)
        with open(args.input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            df_in = pd.DataFrame([data])
        elif isinstance(data, list):
            df_in = pd.DataFrame(data)
        else:
            print("JSON dict veya list olmalı.", file=sys.stderr)
            sys.exit(2)
        preds = predict_from_dataframe(model, feature_cols, df_in)
        df_out = df_in.copy()
        df_out["prediction_price_usd"] = preds
        print(df_out.to_csv(index=False))
        return

    # 3) KV modu
    if args.kv:
        sample = parse_kv_pairs(args.kv)
        df_in = pd.DataFrame([sample])
        pred = predict_from_dataframe(model, feature_cols, df_in).iloc[0]
        print(float(pred))
        return

    # Argüman yoksa yardım mesajı göster
    print("Kullanım örnekleri:")
    print("  python predict.py --input_json sample.json")
    print("  python predict.py --input_csv samples.csv --output_csv preds.csv")
    print('  python predict.py --kv "category=Electronics" --kv "brand=Sony" --kv "country=USA" --kv "city=New York" --kv "shipping_cost=6.0" --kv "seller=DemoSeller" --kv "stock=True" --kv "platform=Amazon" --kv "month=7"')

if __name__ == "__main__":
    main()

