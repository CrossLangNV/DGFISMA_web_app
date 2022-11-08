import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class Attachment {
  constructor(
    public id: string,
    public file: string,
    public url: string,
    public documentId: string,
    public content: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class AttachmentAdapter implements Adapter<Attachment> {
  adapt(item: any): Attachment {
    return new Attachment(
      item.id,
      item.file,
      item.url,
      item.document,
      item.content
    );
  }
  encode(attachment: Attachment): any {
    return {
      id: attachment.id,
      file: attachment.file,
      url: attachment.url,
      document: attachment.documentId,
      content: attachment.content,
    };
  }
}
