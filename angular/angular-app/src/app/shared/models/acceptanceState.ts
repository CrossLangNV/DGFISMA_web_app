import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class AcceptanceState {
  public username: string;
  constructor(
    public id: string,
    public documentId: string,
    public userId: string,
    public value: string
  ) {}
}

@Injectable({
  providedIn: 'root'
})
export class AcceptanceStateAdapter implements Adapter<AcceptanceState> {
  adapt(item: any): AcceptanceState {
    return new AcceptanceState(item.id, item.document, item.user, item.value);
  }
  encode(acceptanceState: AcceptanceState): any {
    return {
      id: acceptanceState.id,
      document: acceptanceState.documentId,
      user: acceptanceState.userId,
      value: acceptanceState.value
    };
  }
}
