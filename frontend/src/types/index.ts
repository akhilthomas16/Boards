/**
 * Named aliases over the generated schema, so components import one short name.
 * Regenerate api.d.ts with the API running:
 *   npx openapi-typescript http://localhost:8001/openapi.json -o src/types/api.d.ts
 */
import type { components } from './api';

type Schemas = components['schemas'];

export type Board = Schemas['BoardResponse'];
export type BoardList = Schemas['BoardListResponse'];
export type Topic = Schemas['TopicResponse'];
export type TopicList = Schemas['TopicListResponse'];
export type Post = Schemas['PostResponse'];
export type PostList = Schemas['PostListResponse'];
export type Profile = Schemas['ProfileResponse'];
export type PublicProfile = Schemas['PublicProfileResponse'];
export type User = Schemas['UserResponse'];
export type UserBrief = Schemas['UserBrief'];
export type SearchResponse = Schemas['SearchResponse'];
export type SearchResult = Schemas['SearchResult'];
export type Notification = Schemas['NotificationResponse'];
