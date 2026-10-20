-- Point the Registry's outgoing mail at Mailpit.
--
-- These are the rows the UI writes when the platform administrator, in the COmanage CO, adds a server under
-- Configuration > Servers (plugin CoreServer.SmtpServers: host mailpit, port 1025, no TLS, no credentials) and then
-- picks it under Configuration > CO Settings > Outgoing SMTP Server. Set on the COmanage CO (id 1), it applies to
-- every CO. Does nothing if the COmanage CO already has an SMTP server.
BEGIN;

WITH server AS (
    INSERT INTO servers (co_id, description, plugin, status, uuid, do_not_clone,
                         created, modified, revision, deleted, actor_identifier)
    SELECT 1, 'Mailpit (workshop mail catcher)', 'CoreServer.SmtpServers', 'A', gen_random_uuid(), false,
           now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC', 0, false, 'workshop-setup'
    WHERE NOT EXISTS (SELECT 1 FROM servers
                      WHERE co_id = 1 AND plugin = 'CoreServer.SmtpServers'
                        AND server_id IS NULL AND deleted IS NOT TRUE)
    RETURNING id
), smtp AS (
    INSERT INTO smtp_servers (server_id, hostname, port, username, password, use_tls,
                              default_from, default_reply_to,
                              created, modified, revision, deleted, actor_identifier)
    SELECT id, 'mailpit', 1025, '', '', false,
           'registry@workshop.test', 'noreply@workshop.test',
           now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC', 0, false, 'workshop-setup'
    FROM server
    RETURNING server_id
)
UPDATE co_settings
   SET email_smtp_server_id = smtp.server_id,
       modified = now() AT TIME ZONE 'UTC',
       actor_identifier = 'workshop-setup'
  FROM smtp
 WHERE co_settings.co_id = 1 AND co_settings.co_setting_id IS NULL AND co_settings.deleted IS NOT TRUE;

COMMIT;
