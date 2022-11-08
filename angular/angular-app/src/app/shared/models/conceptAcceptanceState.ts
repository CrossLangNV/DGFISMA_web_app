import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class ConceptAcceptanceState {
  public username: string;
  constructor(
    public id: string,
    public conceptId: string,
    public userId: string,
    public value: string
  ) {}
}

@Injectable({
  providedIn: 'root'
})
export class ConceptAcceptanceStateAdapter implements Adapter<ConceptAcceptanceState> {
  adapt(item: any): ConceptAcceptanceState {
    return new ConceptAcceptanceState(item.id, item.concept, item.user, item.value);
  }
  encode(acceptanceState: ConceptAcceptanceState): any {
    return {
      id: acceptanceState.id,
      concept: acceptanceState.conceptId,
      user: acceptanceState.userId,
      value: acceptanceState.value
    };
  }
}
