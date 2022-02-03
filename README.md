# django-twitter

This project is twitter backend clone implemented by Python, Django, MySQL, HBase, Amazon S3, Redis and Memcached.

## System Architecture

![architecture](https://user-images.githubusercontent.com/34730615/152260766-e613fdbc-a54d-4159-9565-7a97dff51e7e.png)

## Databases

### MySQL

**User Table** (Django default user, some fields are omitted here):

![image](https://user-images.githubusercontent.com/34730615/152261303-f9a0f3a4-1026-4d40-8a31-e852291b6347.png)

**User Profile Table:**

![image](https://user-images.githubusercontent.com/34730615/152261804-391905fc-131c-4143-a0e5-ac940278b04b.png)

**Friendship Table:**

![image](https://user-images.githubusercontent.com/34730615/152261974-6b875e52-542b-4f50-8574-ff1e037d4dd9.png)

index_together: ('from_user_id', 'created_at'), ('to_user_id', 'created_at') <br />
unique_together: ('from_user_id', 'to_user_id') <br />
ordering: ('-created_at',) <br />

**Tweet Table**

![image](https://user-images.githubusercontent.com/34730615/152262539-024100ab-09b6-4f46-ae7a-0c40ba4a25ac.png)

index_together: ('user', 'created_at') <br />
ordering: ('user', '-created_at') <br />

Note: use denormalization to store comments_count and likes_count in tweet table. 

**Comment Table**

![image](https://user-images.githubusercontent.com/34730615/152264359-1da8c61f-d586-40e4-92a3-bdb1a37fbeec.png)

**Like Table**

![image](https://user-images.githubusercontent.com/34730615/152264444-310c8cdf-a52d-4494-a671-85f3cfc53cdb.png)

index_together: ('content_type', 'object_id', 'created_at') <br />
unique_together: ('user', 'content_type', 'created_at') <br />

**Newsfeed Table**

![image](https://user-images.githubusercontent.com/34730615/152264539-edeff4f7-ee01-49d1-b943-be9f9fe9f099.png)

index_together: ('user', 'created_at') <br />
unique_together: ('user', 'tweet') <br />
ordering: ('user', '-created_at') <br />

**Photo Table**

![image](https://user-images.githubusercontent.com/34730615/152263347-2a34665c-ea0a-4508-83ed-82200de5d6e3.png)

**Tweet Photo Table**

![image](https://user-images.githubusercontent.com/34730615/152263545-145486a1-b366-4db6-a0d3-f38374213daa.png)

index_together = ( <br />
 	('user', 'created_at'), <br />
 	('has_deleted', 'created_at'), <br />
 	('status', 'created_at'), <br />
 	('tweet', 'order'), <br />
) <br />

**Notification Table** (Third Party, some fields are omitted):

![image](https://user-images.githubusercontent.com/34730615/152264132-6029b516-f685-4ea0-a181-24992eebd8c4.png)

index_together = ('recipient', 'unread') <br />


### HBase

**Table twitter_following:** <br />
    row key: from_user_id, created_at <br />
    column key: to_user_id <br />

**Table twitter_followers:** <br />
    row key: to_user_id, created_at <br />
    column key: from_user_id <br />

**Table twitter_newsfeeds:** <br />
    row key: user_id, created_at <br />
    column key: tweet_id <br />

Note: Friendships and newsfeeds can work with either MySQL or HBase. The switch is determined by gatekeeper. See gatekeeper part for more details.

### Amazon S3

Store user avatars and tweet photos.


## APIs

**User and Profile**

`GET /api/users/`   Only admin users have the permission. <br />

`POST /api/accounts/signup/`  It also creates user profile. <br />
`POST /api/accounts/login/` <br />
`POST /api/accounts/logout/` <br />
`GET /api/accounts/login_status/` <br />

`PUT /api/profiles/:profile_id`    Updates nickname and/or avatar. <br />

**Tweet**

`GET /api/tweets/?user_id=xxx`  <br />
Returns has_next_page and results (namely tweets). Every tweet contains photo urls, likes_count, comment_count, has_liked. <br />

`POST /api/tweets/`  <br />
Body should contain `content`, `files` are optional. If files exist, create records in table photo. <br />

`GET /api/tweets/:id`  <br />
Returns tweet details along with photo urls, comments, likes, comments_count, likes_count, has_liked. Every comment has its likes_count and has_liked. <br />

**Friendship**

`POST /api/friendships/:user_id/follow/` <br />
`POST /api/friendships/:user_id/unfollow/` <br />
`GET /api/friendships/:user_id/followings/` <br />
`GET /api/friendships/:user_id/followers/` <br />

**Newsfeed**

`GET /api/newsfeeds/`  <br />
Returns has_next_page and results (list of tweets). Every tweet contains photo urls, likes_count, comments_count and has_liked. <br />

**Comment**

`POST /api/comments/`     Body should contain `tweet_id` and `content`. <br />
`PUT /api/comments/:id`    Body should contain `content`. <br />
`DELETE /api/comments/:id`     <br />
`GET /api/comments/?tweet_id=xxx`   Returns list of comments. Every comment has likes_count and has_liked. <br />
 
**Like**

`POST /api/likes/`      Body should contain `content_type` and `object_id` <br />
`POST /api/likes/cancel/`      Body should contain `content_type` and `object_id` <br />

**Notification**

`GET /api/notifications/`    <br />
`GET /api/notifications/unread-count/` <br />
`POST /api/notifications/mark-all-as-read/` <br />
`PUT /api/notifications/:notification_id`    Body is { ‘unread’: true } or { ‘unread’: false }. <br />


## Cache

Use Redis to cache users’ tweet list and newsfeed list, tweets’ comments_count and likes_counts. <br />

Use Memcached to cache following ids set, users, profiles and tweets.  <br />

Get profile through Memcached. If cache miss, read from db and set in cache.  <br />
Get user by id through Memcached. If cache miss, read from db and set in cache. <br />

When profile is deleted/saved, invalid profile in Memcached.  <br />
When user is deleted/saved, invalid user in Memcached. <br />

When friendship is deleted/saved, invalid from user’s followings in Memcached.  <br />

When tweet is created, push the tweet to the user’s tweet list in Redis. If not exists in cache, read from db and set in cache. <br />
When tweet is saved, invalid the tweet in Memcached. <br />

When comment is created/deleted, increase/decrease comments_count in db, then in Redis. If not found in Redis, back fill from db. <br />
When like is created/deleted against tweet, increase/decrease the tweet’s likes_count in db, then in Redis. If not found in Redis, back fill from db. <br />

When newsfeed is saved, push the newsfeed to user’s newfeed list in Redis.  <br />


## Fanout 

Use push model to fanout newsfeeds. Use Redis as Message Queue Broker to deliver asynchronized tasks.

![push](https://user-images.githubusercontent.com/34730615/152266766-3018223d-aae2-41f2-a486-0698c498ebcd.svg)

When tweet is created, create a fanout task in message queue `default`. Worker will execute `fanout_newsfeeds_main_task` code in an async way. It gets the follower ids, divides by batch size 1000. For every 1000 followers, create task in queue `newsfeeds`, worker will execute `fanout_newsfeeds_batch_task` to batch create records in newsfeed table and push newsfeeds to user’s newfeeds list in Redis. 

As celebrities have millions of followers, fanout would cost lots of resources. We can use pull model instead. 


## Inbox Notifications

When like is created against tweet or comment, send like notification. <br />

When comment is created, send comment notification. <br />


## Pagination

Added page number pagination for followers and followings. <br />

Added endless pagination for listing tweets and newsfeeds. <br />


## Denormalization

Demormalize `likes_count` and `comments_count` in Tweet table. 

`likes_count` / `comments_count` in tweet could be out of sync with the source of truth. Possible solutions are: ttl, sync up at certain interval time. As the issue is very small, we will just leave it for now.


## Rate Limiting

Added rate limiting rules to every API endpoint. Use Memcached for rate limit. 


## Gatekeeper

Added gatekeeper to determine whether switching friendships from MySQL to HBase. <br />
If the percent is set to 0, continue using MySQL. If the percent is set to 100, use HBase. <br />
The key name and percentage are stored in Redis. <br />


