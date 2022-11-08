import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class Comment {
  constructor(
    public id: string,
    public value: string,
    public documentId: string,
    public userId: string,
    public createdAt: Date,
    public username: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class CommentAdapter implements Adapter<Comment> {
  adapt(item: any): Comment {
    return new Comment(
      item.id,
      item.value,
      item.document,
      item.user,
      new Date(item.created_at),
      item.username,
    );
  }
  encode(comment: Comment): any {
    return {
      id: comment.id,
      value: comment.value,
      document: comment.documentId,
      user: comment.userId,
      createdAt: new Date(comment.createdAt).toISOString(),
      username: comment.username,
    };
  }
}
