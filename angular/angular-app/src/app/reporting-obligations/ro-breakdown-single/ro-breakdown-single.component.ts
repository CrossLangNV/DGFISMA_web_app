import {Component, Input, OnInit, ViewEncapsulation} from '@angular/core';

@Component({
  selector: 'app-ro-breakdown-single',
  templateUrl: './ro-breakdown-single.component.html',
  styleUrls: ['./ro-breakdown-single.component.css'],
  encapsulation: ViewEncapsulation.ShadowDom,
})
export class RoBreakdownSingleComponent implements OnInit {

  @Input() roContent: string;

  constructor() { }

  ngOnInit(): void {
  }

}
