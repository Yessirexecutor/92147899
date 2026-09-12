// Vybe API — run with: node --env-file=.env server.js
import Fastify from 'fastify'
import cookie from '@fastify/cookie'
import multipart from '@fastify/multipart'
import fastifyStatic from '@fastify/static'
import postgres from 'postgres'
import argon2 from 'argon2'
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { pipeline } from 'node:stream/promises'
BigInt.prototype.toJSON = function () { return Number(this) }

const sql = postgres(process.env.DATABASE_URL, { max: 10, prepare: false })
const app = Fastify({ logger: true })
app.setErrorHandler((err, req, reply) => {
  req.log.error(err)
  reply.code(err.statusCode || 500).send({ statusCode: err.statusCode || 500, error: err.name, message: err.message })
})

await sql`CREATE TABLE IF NOT EXISTS video_views (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  video_id BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, video_id))`
await sql`CREATE INDEX IF NOT EXISTS idx_video_views_video ON video_views (video_id)`

const TOKEN_DAYS = 30
const sha = s => crypto.createHash('sha256').update(s).digest('hex')

await app.register(cookie)
await app.register(multipart, { limits: { fileSize: 100 * 1024 * 1024 } })
await app.register(fastifyStatic, { root: path.resolve('public') })
await app.register(fastifyStatic, { root: path.resolve('uploads'), prefix: '/uploads/', decorateReply: false })
fs.mkdirSync('uploads/avatars', { recursive: true })
fs.mkdirSync('uploads/videos', { recursive: true })

app.decorateRequest('user', null)
app.addHook('onRequest', async req => {
  if (!req.cookies.sid) return
  const [u] = await sql`
    SELECT u.id, u.username, u.avatar_url, u.bio
    FROM sessions s JOIN users u ON u.id = s.user_id
    WHERE s.token_hash = ${sha(req.cookies.sid)} AND s.expires_at > now()`
  req.user = u || null
  if (req.user) req.user.is_admin = req.user.username === 'vybe'
})
const requireAuth = req => {
  if (!req.user) { const e = new Error('Please log in'); e.statusCode = 401; throw e }
}

async function startSession(reply, userId) {
  const token = crypto.randomBytes(32).toString('hex')
  await sql`INSERT INTO sessions (token_hash, user_id, expires_at)
            VALUES (${sha(token)}, ${userId}, now() + make_interval(days => ${TOKEN_DAYS}))`
  reply.setCookie('sid', token, { httpOnly: true, sameSite: 'lax', path: '/', maxAge: TOKEN_DAYS * 86400 })
}
async function notify(recipientId, actorId, type, videoId) {
  if (recipientId && recipientId !== actorId)
    await sql`INSERT INTO notifications (user_id, actor_id, type, video_id) VALUES (${recipientId}, ${actorId}, ${type}, ${videoId})`
}

app.post('/api/register', async (req, reply) => {
  const { username = '', password = '' } = req.body || {}
  if (!/^[a-z0-9_]{3,20}$/.test(username)) return reply.code(400).send({ error: 'Username: 3-20 chars, a-z 0-9 _' })
  if (String(password).length < 8) return reply.code(400).send({ error: 'Password must be 8+ characters' })
  try {
    const [user] = await sql`INSERT INTO users (username, password_hash)
      VALUES (${username}, ${await argon2.hash(password)}) RETURNING id, username, avatar_url, bio`
    await startSession(reply, user.id)
    return { user }
  } catch (e) {
    return reply.code(e.code === '23505' ? 409 : 400).send({ error: e.code === '23505' ? 'Username taken' : 'Bad request' })
  }
})
app.post('/api/login', async (req, reply) => {
  const { username = '', password = '' } = req.body || {}
  const [u] = await sql`SELECT * FROM users WHERE username = ${username}`
  if (!u || !(await argon2.verify(u.password_hash, password)))
    return reply.code(401).send({ error: 'Wrong username or password' })
  await startSession(reply, u.id)
  return { user: { id: u.id, username: u.username, avatar_url: u.avatar_url, bio: u.bio } }
})
app.post('/api/logout', async req => {
  if (req.cookies.sid) await sql`DELETE FROM sessions WHERE token_hash = ${sha(req.cookies.sid)}`
  req.user = null
  return {}
})
app.get('/api/me', async (req, reply) => {
  if (!req.user) return reply.code(401).send({ error: 'Not logged in' })
  return { user: req.user }
})
app.patch('/api/me', async (req, reply) => {
  requireAuth(req)
  const bio = String(req.body?.bio || '').slice(0, 200)
  const [user] = await sql`UPDATE users SET bio = ${bio} WHERE id = ${req.user.id} RETURNING id, username, avatar_url, bio`
  return { user }
})
app.post('/api/me/avatar', async (req, reply) => {
  requireAuth(req)
  const f = await req.file()
  const ext = path.extname(f.filename || '').toLowerCase()
  if (!['.jpg', '.jpeg', '.png', '.webp'].includes(ext)) return reply.code(400).send({ error: 'Image only' })
  const name = crypto.randomUUID() + ext
  await pipeline(f.file, fs.createWriteStream(path.join('uploads/avatars', name)))
  const avatar_url = `/uploads/avatars/${name}`
  await sql`UPDATE users SET avatar_url = ${avatar_url} WHERE id = ${req.user.id}`
  return { avatar_url }
})

app.get('/api/feed', async req => {
  const meId = req.user?.id ?? null
  let q = sql`
    SELECT v.id, u.username, u.avatar_url, v.caption, v.views::int AS views, v.created_at,
           COALESCE(v.src_hls, v.src_mp4) AS src, v.thumb_url AS thumb,
           (SELECT count(*) FROM likes l WHERE l.video_id = v.id)::int AS likes,
           (SELECT count(*) FROM comments c WHERE c.video_id = v.id)::int AS comments,
           (EXISTS (SELECT 1 FROM likes l WHERE l.video_id = v.id AND l.user_id = ${meId})) AS liked,
           (EXISTS (SELECT 1 FROM follows f WHERE f.followee_id = v.user_id AND f.follower_id = ${meId})) AS following
    FROM videos v JOIN users u ON u.id = v.user_id
    WHERE v.status = 'ready'`
  const [ts, cid] = decodeURIComponent(req.query.cursor || '').split(',')
  if (ts && cid)
    q = sql`${q} AND (v.created_at, v.id) < (${ts}::timestamptz, ${Number(cid)}::bigint)`
  const rows = await sql`${q} ORDER BY v.created_at DESC, v.id DESC LIMIT 10`
  const last = rows.at(-1)
  return { videos: rows, next_cursor: last ? `${new Date(last.created_at).toISOString()},${last.id}` : null }
})
app.post('/api/videos', async (req, reply) => {
  requireAuth(req)
  const f = await req.file()
  if (!f) return reply.code(400).send({ error: 'No file' })
  const name = crypto.randomUUID() + (path.extname(f.filename || '') || '.mp4')
  await pipeline(f.file, fs.createWriteStream(path.join('uploads/videos', name)))
  const caption = String(f.fields.caption?.value || '').slice(0, 300)
  const [v] = await sql`INSERT INTO videos (user_id, caption, status, src_mp4)
                        VALUES (${req.user.id}, ${caption}, 'ready', ${'/uploads/videos/' + name}) RETURNING id`
  return { id: v.id, status: 'ready' }
})
app.post('/api/videos/:id/view', async req => {
  const id = Number(req.params.id)
  if (!req.user) return {}
  const ins = await sql`INSERT INTO video_views (user_id, video_id) VALUES (${req.user.id}, ${id}) ON CONFLICT DO NOTHING RETURNING video_id`
  if (ins.length) await sql`UPDATE videos SET views = views + 1 WHERE id = ${id}`
  return {}
})
app.post('/api/videos/:id/like', async (req, reply) => {
  requireAuth(req)
  const id = Number(req.params.id)
  const [video] = await sql`SELECT user_id FROM videos WHERE id = ${id}`
  if (!video) return reply.code(404).send({ error: 'No such video' })
  const removed = await sql`DELETE FROM likes WHERE user_id = ${req.user.id} AND video_id = ${id} RETURNING video_id`
  if (removed.length === 0) {
    await sql`INSERT INTO likes (user_id, video_id) VALUES (${req.user.id}, ${id}) ON CONFLICT DO NOTHING`
    await notify(video.user_id, req.user.id, 'like', id)
  }
  const [{ likes }] = await sql`SELECT count(*)::int AS likes FROM likes WHERE video_id = ${id}`
  return { liked: removed.length === 0, likes }
})

app.get('/api/videos/:id/comments', async req => {
  const rows = await sql`
    SELECT c.id, c.body, c.created_at, u.username
    FROM comments c JOIN users u ON u.id = c.user_id
    WHERE c.video_id = ${Number(req.params.id)}
    ORDER BY c.created_at DESC, c.id DESC LIMIT 50`
  return { comments: rows, next_cursor: null }
})
app.post('/api/videos/:id/comments', async (req, reply) => {
  requireAuth(req)
  const id = Number(req.params.id), body = String(req.body?.body || '').trim().slice(0, 500)
  if (!body) return reply.code(400).send({ error: 'Empty comment' })
  const [video] = await sql`SELECT user_id FROM videos WHERE id = ${id}`
  if (!video) return reply.code(404).send({ error: 'No such video' })
  const [c] = await sql`INSERT INTO comments (video_id, user_id, body) VALUES (${id}, ${req.user.id}, ${body})
                        RETURNING id, body, created_at`
  await notify(video.user_id, req.user.id, 'comment', id)
  const [{ comments }] = await sql`SELECT count(*)::int AS comments FROM comments WHERE video_id = ${id}`
  return { ...c, username: req.user.username, comments }
})

app.post('/api/users/:username/follow', async (req, reply) => {
  requireAuth(req)
  const [target] = await sql`SELECT id FROM users WHERE username = ${req.params.username}`
  if (!target) return reply.code(404).send({ error: 'No such user' })
  if (target.id === req.user.id) return reply.code(400).send({ error: "Can't follow yourself" })
  const removed = await sql`DELETE FROM follows WHERE follower_id = ${req.user.id} AND followee_id = ${target.id} RETURNING followee_id`
  if (removed.length === 0) {
    await sql`INSERT INTO follows (follower_id, followee_id) VALUES (${req.user.id}, ${target.id}) ON CONFLICT DO NOTHING`
    await notify(target.id, req.user.id, 'follow', null)
  }
  const [{ followers }] = await sql`SELECT count(*)::int AS followers FROM follows WHERE followee_id = ${target.id}`
  return { following: removed.length === 0, followers }
})
app.get('/api/users/:username', async (req, reply) => {
  const [u] = await sql`SELECT id, username, avatar_url, bio FROM users WHERE username = ${req.params.username}`
  if (!u) return reply.code(404).send({ error: 'No such user' })
  const [[{ followers }], [{ following }]] = await Promise.all([
    sql`SELECT count(*)::int AS followers FROM follows WHERE followee_id = ${u.id}`,
    sql`SELECT count(*)::int AS following FROM follows WHERE follower_id = ${u.id}`,
  ])
  const videos = await sql`
    SELECT id, thumb_url AS thumb, views::int AS views FROM videos
    WHERE user_id = ${u.id} AND status = 'ready'
    ORDER BY created_at DESC, id DESC LIMIT 60`
  return {
    user: { username: u.username, avatar_url: u.avatar_url, bio: u.bio },
    stats: { followers, following },
    videos,
    following: req.user
      ? (await sql`SELECT 1 AS x FROM follows WHERE follower_id = ${req.user.id} AND followee_id = ${u.id}`).length > 0
      : false,
  }
})

app.get('/api/notifications', async req => {
  requireAuth(req)
  const notifications = await sql`
    SELECT n.id, n.type, n.video_id, n.read, n.created_at, a.username AS actor, a.avatar_url
    FROM notifications n LEFT JOIN users a ON a.id = n.actor_id
    WHERE n.user_id = ${req.user.id}
    ORDER BY n.created_at DESC, n.id DESC LIMIT 50`
  const [{ unread }] = await sql`SELECT count(*)::int AS unread FROM notifications WHERE user_id = ${req.user.id} AND read = false`
  return { notifications, unread }
})
app.post('/api/notifications/read', async req => {
  requireAuth(req)
  await sql`UPDATE notifications SET read = true WHERE user_id = ${req.user.id}`
  return {}
})

const ADMIN = 'vybe'
app.delete('/api/videos/:id', async (req, reply) => {
  requireAuth(req)
  const id = Number(req.params.id)
  const [v] = await sql`SELECT user_id, src_mp4 FROM videos WHERE id = ${id}`
  if (!v) return reply.code(404).send({ error: 'No such video' })
  const mine = String(v.user_id) === String(req.user.id)
  if (!mine && req.user.username !== ADMIN) return reply.code(403).send({ error: 'Not allowed' })
  await sql`DELETE FROM videos WHERE id = ${id}`
  if (v.src_mp4) { try { fs.unlinkSync(path.join('.', v.src_mp4)) } catch {} }
  return { deleted: true }
})
app.delete('/api/comments/:cid', async (req, reply) => {
  requireAuth(req)
  const cid = Number(req.params.cid)
  const [c] = await sql`SELECT user_id FROM comments WHERE id = ${cid}`
  if (!c) return reply.code(404).send({ error: 'No such comment' })
  const mine = String(c.user_id) === String(req.user.id)
  if (!mine && req.user.username !== ADMIN) return reply.code(403).send({ error: 'Not allowed' })
  await sql`DELETE FROM comments WHERE id = ${cid}`
  return { deleted: true }
})

const port = Number(process.env.PORT || 3000)
app.listen({ port, host: '0.0.0.0' }).then(() => console.log(`> Vybe running: http://localhost:${port}`))
