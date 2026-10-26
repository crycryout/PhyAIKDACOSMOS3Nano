from pathlib import Path
import argparse,gzip,hashlib,json,shutil
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);p.add_argument("--folder",required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();t=a.task
src=t/"results"/a.folder/"candidate-dynamic.trace.json";dst=src.with_suffix(src.suffix+".gz");assert src.is_file() and not dst.exists()
with src.open("rb") as source,dst.open("xb") as target:
    with gzip.GzipFile(filename="",mode="wb",fileobj=target,compresslevel=6,mtime=0) as zipped:shutil.copyfileobj(source,zipped,8*1024*1024)
expected=hashlib.sha256(src.read_bytes()).hexdigest();actual=hashlib.sha256()
with gzip.open(dst,"rb") as stream:
    for chunk in iter(lambda:stream.read(8*1024*1024),b""):actual.update(chunk)
assert actual.hexdigest()==expected
row=dict(source=str(src.relative_to(t)),archive=str(dst.relative_to(t)),source_sha256=expected,compressed_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),original_bytes=src.stat().st_size,compressed_bytes=dst.stat().st_size,decompressed_sha256_matches=True)
with a.output.open("x") as stream:json.dump(dict(complete=True,archives=[row]),stream,indent=2);stream.write("\n")
print(json.dumps(row,indent=2))
