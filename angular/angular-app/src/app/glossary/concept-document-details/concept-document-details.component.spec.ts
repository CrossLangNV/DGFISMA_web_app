import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ConceptDocumentDetailsComponent } from './concept-document-details.component';

describe('ConceptDocumentDetailsComponent', () => {
  let component: ConceptDocumentDetailsComponent;
  let fixture: ComponentFixture<ConceptDocumentDetailsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ConceptDocumentDetailsComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ConceptDocumentDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
