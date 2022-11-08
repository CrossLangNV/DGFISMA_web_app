import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class Tag {
  constructor(
    public id: string,
    public value: string,
    public documentId: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class TagAdapter implements Adapter<Tag> {
  adapt(item: any): Tag {
    return new Tag(item.id, item.value, item.document);
  }
  encode(tag: Tag): any {
    return {
      id: tag.id,
      value: tag.value,
      document: tag.documentId,
    };
  }
}
