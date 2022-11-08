import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class ConceptComment {
  constructor(
    public id: string,
    public value: string,
    public conceptId: string,
    public userId: string,
    public createdAt: Date,
    public username: string,
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class ConceptCommentAdapter implements Adapter<ConceptComment> {
  adapt(item: any): ConceptComment {
    return new ConceptComment(
      item.id,
      item.value,
      item.concept,
      item.user,
      new Date(item.created_at),
      item.username,
    );
  }

  // TODO: Refactor this capital letter for concept in front and backend
  encode(conceptComment: ConceptComment): any {
    const stringDate = new Date(conceptComment.createdAt).toISOString();
    return {
      id: conceptComment.id,
      value: conceptComment.value,
      Concept: conceptComment.conceptId,
      user: conceptComment.userId,
      createdAt: stringDate,
      username: conceptComment.username,
    };
  }
}
