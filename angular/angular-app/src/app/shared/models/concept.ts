import { Injectable } from '@angular/core';
import { Adapter } from './adapter';
import {AcceptanceState} from './acceptanceState';
export interface ConceptResults {
  count: number;
  count_total: number;
  count_unvalidated: number;
  count_rejected: number;
  count_validated: number;
  count_autorejected: number;
  count_autovalidated: number;
  next: string;
  previous: string;
  results: Concept[];
}
export class Concept {
  constructor(
    public id: string,
    public name: string,
    public definition: string,
    public documentIds: string[],
    public tags: string[],
    public commentIds: string[],
    public acceptanceStates: AcceptanceState[],
    public acceptanceStatesCount: string[],
    public acceptanceState: string,
    public acceptanceStateValue: string,
    public other: Concept[]
  ) {}
}
export interface LemmaResults {
  count: number;
  next: string;
  previous: string;
  results: Lemma[];
}
export class Lemma {
  constructor(
    public id: string,
    public name: string,
    public concepts: Concept[]
  ) {}
}

@Injectable({
  providedIn: 'root',
})
export class ConceptAdapter implements Adapter<Concept> {
  adapt(item: any): Concept {
    return new Concept(
      item.id,
      item.name,
      item.definition,
      item.documents,
      item.tags,
      item.comments,
      item.acceptance_states,
      item.acceptance_states_count,
      item.acceptance_state,
      item.acceptance_state_value,
      item.other
    );
  }
  encode(concept: Concept): any {
    return {
      id: concept.id,
      name: concept.name,
      definition: concept.definition,
      documents: concept.documentIds,
      tags: concept.tags,
      comments: concept.commentIds,
      acceptance_states: concept.acceptanceStates,
      acceptance_states_count: concept.acceptanceStatesCount,
      acceptance_state: concept.acceptanceState,
      acceptance_state_value: concept.acceptanceStateValue,
      other: concept.other,
    };
  }
}
