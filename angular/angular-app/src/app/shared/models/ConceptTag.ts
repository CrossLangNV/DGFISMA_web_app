import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class ConceptTag {
  constructor(
    public id: string,
    public value: string,
    public conceptId: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class ConceptTagAdapter implements Adapter<ConceptTag> {
  adapt(item: any): ConceptTag {
    return new ConceptTag(item.id, item.value, item.concept);
  }
  encode(tag: ConceptTag): any {
    return {
      id: tag.id,
      value: tag.value,
      concept: tag.conceptId,
    };
  }
}
