import { Injectable } from '@angular/core';
import { Adapter } from './adapter';
import {Concept} from "./concept";
import {AcceptanceState} from './acceptanceState';

export class RoResults {
  constructor(
    public count: number,
    public count_unvalidated: number,
    public count_total: number,
    public count_rejected: number,
    public count_validated: number,
    public count_autorejected: number,
    public count_autovalidated: number,
    public next: string,
    public previous: string,
    public results: ReportingObligation[]
  ) {}
}

export class ReportingObligation {
  constructor(
    public id: string,
    public name: string,
    public definition: string,
    public documentIds: string[],
    public tags: string[],
    public commentIds: string[],
    public concept: string,
    public acceptanceStates: AcceptanceState[],
    public acceptanceStatesCount: string[],
    public acceptanceState: string,
    public acceptanceStateValue: string,
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class RoAdapter implements Adapter<ReportingObligation> {
  adapt(item: any): ReportingObligation {
    return new ReportingObligation(
      item.id,
      item.name,
      item.definition,
      item.documents,
      item.tags,
      item.comments,
      item.concept,
      item.acceptance_states,
      item.acceptance_states_count,
      item.acceptance_state,
      item.acceptance_state_value,
    );
  }
  encode(ro: ReportingObligation): any {
    return {
      id: ro.id,
      name: ro.name,
      definition: ro.definition,
      documents: ro.documentIds,
      tags: ro.tags,
      comments: ro.commentIds,
      concept: ro.concept,
      acceptance_states: ro.acceptanceStates,
      acceptance_states_count: ro.acceptanceStatesCount,
      acceptance_state: ro.acceptanceState,
      acceptance_state_value: ro.acceptanceStateValue
    };
  }
}
