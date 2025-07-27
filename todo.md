# Dev TODO

## Maintenance

1. OOO principles. encapsulate the crawler state and behaviour in a class `Crawler` instead of the global vars currently used. parameterize the configs into a pydantic model. add error handling for missing env vars (e.g. start_url, password)
2. concurrency. use `asyncio.Queue` for the scraper queue. page concurrency doesn't appear to be working properly - not erroring, but not actually async.
3. increase modularity. `process_page()` should be broken into smaller modules.
4. testing. small unit tests for helpers, mock-based integration test for key flows (e.g. html download, pdf download, diffing, summarization).
