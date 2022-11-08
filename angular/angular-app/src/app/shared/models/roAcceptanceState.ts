import { Injectable } from '@angular/core';
import { Adapter } from './adapter';

export class RoAcceptanceState {
  public username: string;
  constructor(
    public id: string,
    public roId: string,
    public userId: string,
    public value: string
  ) {}
}

@Injectable({
  providedIn: 'root'
})
export class RoAcceptanceStateAdapter implements Adapter<RoAcceptanceState> {
  adapt(item: any): RoAcceptanceState {
    return new RoAcceptanceState(item.id, item.reporting_obligation, item.user, item.value);
  }
  encode(acceptanceState: RoAcceptanceState): any {
    return {
      id: acceptanceState.id,
      reporting_obligation: acceptanceState.roId,
      user: acceptanceState.userId,
      value: acceptanceState.value
    };
  }
}
