import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class Website {
  constructor(
    public id: string,
    public name: string,
    public url: string,
    public content: string,
    public totalDocuments: number
  ) {}
}

@Injectable({
  providedIn: 'root'
})
export class WebsiteAdapter implements Adapter<Website> {
  adapt(item: any): Website {
    return new Website(
      item.id,
      item.name,
      item.url,
      item.content,
      item.total_documents
    );
  }
  encode(website: Website): any {
    return {
      id: website.id,
      name: website.name,
      url: website.url,
      content: website.content,
      total_documents: website.totalDocuments
    };
  }
}
