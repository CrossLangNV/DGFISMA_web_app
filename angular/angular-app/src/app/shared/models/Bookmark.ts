import { Injectable } from '@angular/core';
import { Adapter } from './adapter';
import { Document } from './document';

export class Bookmark {
  constructor(
    public user: string,
    public document: Document,
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class BookmarkAdapter implements Adapter<Bookmark> {
  adapt(item: any): Bookmark {
    return new Bookmark(item.user, item.document);
  }
  encode(bookmark: Bookmark): any {
    return {
      user: bookmark.user,
      document: bookmark.document.id,
    };
  }
}
