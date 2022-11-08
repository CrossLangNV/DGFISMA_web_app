import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { RoDetailComponent } from './ro-detail.component';

describe('RoDetailComponent', () => {
    let component: RoDetailComponent;
    let fixture: ComponentFixture<RoDetailComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [RoDetailComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(RoDetailComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
