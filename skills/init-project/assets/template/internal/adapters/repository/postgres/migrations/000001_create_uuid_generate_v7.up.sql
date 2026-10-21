-- uuid_generate_v7 returns an RFC 9562 UUIDv7: the first 48 bits are the Unix
-- epoch in milliseconds, the rest comes from gen_random_uuid() with the version
-- nibble rewritten to 7. PostgreSQL 17 has no built-in uuidv7() (added in 18),
-- so a DB-generated uuid primary key uses DEFAULT uuid_generate_v7() instead of
-- gen_random_uuid(). It is created unqualified so it lands in the service schema
-- set by search_path, and CREATE OR REPLACE keeps the migration idempotent where
-- the function was already created by hand.
CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid
LANGUAGE sql VOLATILE PARALLEL SAFE AS $$
  SELECT encode(
    set_bit(set_bit(
      overlay(pg_catalog.uuid_send(pg_catalog.gen_random_uuid())
              PLACING substring(pg_catalog.int8send(floor(extract(epoch FROM pg_catalog.clock_timestamp()) * 1000)::bigint) FROM 3)
              FROM 1 FOR 6),
    52, 1), 53, 1), 'hex')::uuid;
$$;
