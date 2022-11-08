import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class RoTag {
  constructor(
    public id: string,
    public value: string,
    public roId: string
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class RoTagAdapter implements Adapter<RoTag> {
  adapt(item: any): RoTag {
    return new RoTag(item.id, item.value, item.reporting_obligation);
  }
  encode(tag: RoTag): any {
    return {
      id: tag.id,
      value: tag.value,
      reporting_obligation: tag.roId,
    };
  }
}
