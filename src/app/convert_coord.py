import argparse
import pandas as pd
from pyproj import Transformer

def convert_single(x, y, epsg_from):
    transformer = Transformer.from_crs(epsg_from, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon

def convert_csv(input_file, output_file, epsg_from):
    df = pd.read_csv(input_file)

    if "x" not in df.columns or "y" not in df.columns:
        raise ValueError("CSV 파일에 'x', 'y' 컬럼이 있어야 합니다.")

    transformer = Transformer.from_crs(epsg_from, "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(df["x"].values, df["y"].values)

    df["lon"] = lons
    df["lat"] = lats

    df.to_csv(output_file, index=False)
    print(f"✅ 변환 완료 → {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="공공데이터 TM 좌표 → WGS84 변환기")
    parser.add_argument("--mode", choices=["single", "csv"], required=True)
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)
    parser.add_argument("--epsg", type=int, default=2097)
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str)

    args = parser.parse_args()

    if args.mode == "single":
        if args.x is None or args.y is None:
            print("❌ single 모드에서는 --x, --y 필요")
        else:
            lat, lon = convert_single(args.x, args.y, args.epsg)
            print(f"✅ 변환 결과 → 위도(lat): {lat:.6f}, 경도(lon): {lon:.6f}")
    elif args.mode == "csv":
        if args.input is None or args.output is None:
            print("❌ csv 모드에서는 --input, --output 필요")
        else:
            convert_csv(args.input, args.output, args.epsg) 