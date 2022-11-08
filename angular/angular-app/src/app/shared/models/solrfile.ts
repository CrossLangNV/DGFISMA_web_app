import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class SolrFile {
  public documentTitle: string;
  public website: string;
  public rawFile: string;

  constructor(
    public id: string,
    public documentId: string,
    public url: string,
    public date: Date,
    public language: string,
    public docType: string,
    public content: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class SolrFileAdapter implements Adapter<SolrFile> {
  adapt(item: any): SolrFile {
    const parsedDate = item.attr_date ? new Date(item.attr_date[0]) : new Date();
    return new SolrFile(
      item.id,
      item.attr_document_id[0],
      item.attr_url[0],
      parsedDate,
      item.language,
      item.doc_type,
      item.content
    );
  }
  encode(solrFile: SolrFile): any {
    return {
      id: solrFile.id,
      attr_document_id: solrFile.documentId,
      attr_url: solrFile.url,
      attr_date: solrFile.date,
      language: solrFile.language,
      doc_type: solrFile.docType,
      content: solrFile.content,
    };
  }
}
