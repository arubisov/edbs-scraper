from openai import OpenAI
import glob, os, time

client = OpenAI()

# Create it once; keep the ID for all future updates
vs = client.vector_stores.create(name="edbs-files")

folder = "scraped_text"                     # wherever your script writes them
paths  = glob.glob(os.path.join(folder, "*.txt"))
streams = [open(p, "rb") for p in paths]

# helper handles upload + polling until the text is embedded
batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vs.id,
            files=streams
)
assert batch.status == "completed", batch
for fp in streams: fp.close()
print(f"Added {batch.file_counts.completed} files to {vs.id}")