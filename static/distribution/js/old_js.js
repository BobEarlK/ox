$(document).ready(function () {
    // add class for alternating rows
    $('.stream-row:odd').addClass('odd-row');


  $('.select-provider').click(function() {
    // if deselect, do nothing; otherwise, get selection data
    if($(this).children('option:selected').val() != ''){
      $selectedProviderIDString = $(this).children('option:selected').val(); // gives str of provider ID, e.g. '2'
      $selectedProviderCell = $(this).closest('#id_provider_cell');
      $selectedStreamRow = $(this).closest('.stream-row');
      $otherStreamRows = $('.stream-row').not($selectedStreamRow);
      $selectedDay = $selectedProviderCell.prevAll().length - 1;
      $laterCells = $selectedProviderCell.nextAll();


      $dayIndicesOfCellsWithSameProvider = [$selectedDay]; // array of later cell indices which have the selected provider as a choice for that stream
      $laterCells.each(function(index){
        $options = $(this).find('option');
        $options.each(function(){
            if($(this).val()==$selectedProviderIDString){
              $selectedProviderIDNumber = parseInt($selectedProviderIDString);
               $dayIndicesOfCellsWithSameProvider.push(index+1+$selectedDay);
               };
      });

        });
      // dayIndices. . . now populated
      console.log($dayIndicesOfCellsWithSameProvider.length);
      console.log($dayIndicesOfCellsWithSameProvider);
      // finally, loop through the day indices and 1) set other streams with same provider to empty,
      // and 2)
   $.each($dayIndicesOfCellsWithSameProvider, function(index,value){
     // set other streams on same day with same provider to empty
     $otherStreamRows.each(function(){
       $otherStreamSameDateCell = $(this).children('#id_provider_cell').eq(value);
       console.log($otherStreamSameDateCell.find('select').val());
       if($otherStreamSameDateCell.find('select').val() == $selectedProviderIDString){
         $otherStreamSameDateCell.find('select').val('');
       };
     });
     // set the current stream provider to the selected provider
       $sameStreamOtherDateCell = $selectedStreamRow.children('#id_provider_cell').eq(value);
       $sameStreamOtherDateCell.find('select').val($selectedProviderIDString);
   });
    };
  });
});
