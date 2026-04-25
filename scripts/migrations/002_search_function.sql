-- Updated search() function with ghl_notes branch.
-- Run this in Supabase: Dashboard → SQL Editor → paste → Run
-- Re-run this file each time a new text-bearing table is added.

drop function if exists search(text, vector, integer);

create or replace function search(
  query_text text,
  query_embedding vector(1024),
  match_limit int default 10
)
returns table (
  source_type text,
  source_id text,
  title text,
  content text,
  metadata jsonb,
  rerank_score float,
  synced_at timestamptz
)
language plpgsql
stable
as $$
declare
  voyage_api_key text;
  candidate_json jsonb;
  rerank_response jsonb;
begin
  create temp table if not exists _candidates (
    source_type text,
    source_id text,
    title text,
    content text,
    metadata jsonb,
    rrf_score float,
    synced_at timestamptz
  ) on commit drop;

  delete from _candidates;

  -- === ghl_notes branch ===
  insert into _candidates
  select
    coalesce(s.source_type, k.source_type),
    coalesce(s.source_id, k.source_id),
    coalesce(s.title, k.title),
    coalesce(s.content, k.content),
    coalesce(s.metadata, k.metadata),
    coalesce(s.sem_rrf, 0.0) + coalesce(k.kw_rrf, 0.0),
    coalesce(s.synced_at, k.synced_at)
  from (
    select
      'ghl_notes'::text as source_type,
      source_id,
      ''::text as title,
      body as content,
      metadata,
      1.0 / (60 + row_number() over (order by embedding <=> query_embedding)) as sem_rrf,
      _synced_at as synced_at
    from ghl_notes
    where embedding is not null
    order by embedding <=> query_embedding
    limit match_limit * 3
  ) s
  full outer join (
    select
      'ghl_notes'::text as source_type,
      source_id,
      ''::text as title,
      body as content,
      metadata,
      1.0 / (60 + row_number() over (order by ts_rank(search_tsv, websearch_to_tsquery('english', query_text)) desc)) as kw_rrf,
      _synced_at as synced_at
    from ghl_notes
    where search_tsv @@ websearch_to_tsquery('english', query_text)
    limit match_limit * 3
  ) k on s.source_id = k.source_id;

  if (select count(*) from _candidates) = 0 then
    return;
  end if;

  -- Attempt Voyage reranking; fall back to RRF on any failure
  begin
    select decrypted_secret into voyage_api_key
    from vault.decrypted_secrets
    where name = 'voyage_api_key';

    if voyage_api_key is null then
      raise exception 'no voyage key in vault';
    end if;

    candidate_json := (select jsonb_agg(content order by rrf_score desc) from _candidates);

    select content::jsonb into rerank_response
    from net.http_post(
      url := 'https://api.voyageai.com/v1/rerank',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || voyage_api_key,
        'Content-Type', 'application/json'
      ),
      body := jsonb_build_object(
        'query', query_text,
        'documents', candidate_json,
        'model', 'rerank-2',
        'top_k', match_limit
      )::text,
      timeout_milliseconds := 2000
    );

    return query
    with ranked as (
      select
        (r->>'index')::int as doc_idx,
        (r->>'relevance_score')::float as score
      from jsonb_array_elements(rerank_response->'data') r
    ),
    indexed as (
      select *, row_number() over (order by rrf_score desc) - 1 as idx
      from _candidates
    )
    select
      c.source_type, c.source_id, c.title, c.content, c.metadata,
      r.score as rerank_score,
      c.synced_at
    from ranked r
    join indexed c on c.idx = r.doc_idx
    order by r.score desc
    limit match_limit;

  exception when others then
    return query
    select source_type, source_id, title, content, metadata, rrf_score, synced_at
    from _candidates
    order by rrf_score desc
    limit match_limit;
  end;
end;
$$;
