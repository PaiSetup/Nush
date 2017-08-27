package com.paijan.algorytmy;

import java.util.Random;

class Sorting {

	//--------------------------------------------------------------------- Testowanie

	private static class Test {
		static Random random = new Random();
		interface SortFunction {
			void sort(int[] w);
		}
		public static void main(String[] args) {
			//int[] w = generateTestArray(32);
			//shellSort(w);
			//System.out.println("Sorted: " + isSorted(w));


			new Test().testAll();
		}


		void testAll() {
			String[] names = new String[] {"naiveSort", "bubbleSort", "insertionSort", "shellSort", "selectionSort", "heapSort", "mergeSort", "quickSort"};
			SortFunction[] functions = new SortFunction[] {
					Sorting::naiveSort, Sorting::bubbleSort, Sorting::insertionSort, Sorting::shellSort,
					Sorting::selectionSort, Sorting::heapSort, Sorting::mergeSort, Sorting::quickSort
			};
			int[] sizes = generateArraySizes();

			System.out.print("Size;");
			for (String name : names) {
				System.out.printf("%s;", name);
			}
			System.out.println();

			for (int size : sizes) {
				System.out.printf("%d;", size);
				for (SortFunction function : functions) {
					int[] w = generateTestArray(size);

					long start = System.nanoTime();
					function.sort(w);
					long time = System.nanoTime() - start;

					float microseconds = time/1000.f;
					boolean passed = isSorted(w);

					if (passed) System.out.printf("%f;", microseconds);
					else System.out.printf("FAIL;");
				}
				System.out.println();
			}
		}

		static int[] generateArraySizes() {
			int sizesCount = 40;
			int sizesStep = 500;
			int[] sizes = new int[sizesCount];
			for(int i=0; i<sizesCount; i++) {
				sizes[i] = (i+1) * sizesStep;
			}
			return sizes;
		}

		static int[] generateTestArray(int size) {
			int[] result = new int[size];
			for(int i=0; i<size; i++) {
				result[i] = random.nextInt();
			}
			return result;
		}

		static boolean isSorted(int[] w) {
			for(int i=1; i<w.length; i++) {
				if(w[i] < w[i-1]) return false;
			}
			return true;
		}
	}

	//--------------------------------------------------------------------- Algorytmy

	static void naiveSort(int[] w) {
		//O(n^2)
		//Zerowy element porównujemy ze wszystkimi po prawej (od 1 do n)
		//Pierwszy element porównujemy ze wszystkimi po prawej (od 2 do n), z tymi po lewej już nie trzeba
		//Z ostatnim elementem nic już nie robimy, bo nie ma nic po prawej
		//Po zakończeniu x obiegów na początku tablicy jest x posortowanych elementów
		for (int i = 0; i < w.length - 1; i++) {
			for (int j = i + 1; j < w.length; j++)
				if (w[j] < w[i]) {
					int swap = w[j];
					w[j] = w[i];
					w[i] = swap;
				}
		}
	}

	static void bubbleSort(int[] w) {
		//O(n^2)
		//Porównujemy kolejne pary sąsiednich elementów: (0 i 1), (1 i 2), (2 i 3),...
		//Po x obiegach zewnętrznej pętli mamy x posortowanych elementów na końcu
		//Dzięki temu każdy kolejny obieg jest o 1 krótszy, bo nie sprawdzamy ostatnich liczb
		//Dlatego w wewnętrznej pętli warunek j < length - i - 1
		for (int i = 0; i < w.length - 1; i++) {
			for (int j = 0; j < w.length - i - 1; j++) {
				if (w[j] > w[j + 1]) {
					int swap = w[j];
					w[j] = w[j + 1];
					w[j + 1] = swap;
				}
			}
		}
	}

	static void insertionSort(int[] w) {
		//Tablica ma dwie części: z lewej jest posortowana, z prawej nie
		//Uznajemy że pierwszy element jest posortowaną częścią o długości 1
		//Reszta po prawej jest nieposortowana
		//Dodajemy kolejne elementy z prawej części do części posortowanej
		//tak, aby część ta pozostała posortowana
		//By to zrobić, porównujemy dodawany element z kolejnymi posortowanymi aż
		//Znajdziemy miejsce gdzie powinien się znaleźć; rozsuwamy posortowane elementy

		//i jest licznikiem posortowanych liczb
		for (int i = 1; i < w.length; i++) {
			int value = w[i]; //wartość wstawianej liczby
			//ta pętla szuka miejsca dla wstawianej liczby, rozsuwa elementy tak długo,
			//aż natrafi na element mniejszy od value lub skończą się elementy
			int j; //j wskazuje na pozycje liczby, która ma być przesunięta w prawo
			for (j = i; j > 0 && value < w[j-1]; j--) {
				w[j] = w[j-1];
			}
			w[j] = value; //wstawienie wartości
		}
	}

	static void shellSort(int[] w) {
		//wykonujemy insertionSort na elementach oddalonych o k przy k malejącym do 1
		//złożoność zależy od kolejnych wartości k, tutaj przyjęto (...),31,15,7,3,1
		//co daje złożoność n^(1.5)

		//k = 2^(floor(log(2, n)) - 1
		int bits = (int) (Math.log10(w.length)/Math.log10(2));
		int k = 1;
		while(bits > 0) {
			k *= 2;
			bits--;
		}
		k -= 1;

		while(k >= 1) {
			for (int i = k; i < w.length; i+=k) {
				int value = w[i]; //wartość wstawianej liczby
				//ta pętla szuka miejsca dla wstawianej liczby, rozsuwa elementy tak długo,
				//aż natrafi na element mniejszy od value lub skończą się elementy
				int j; //j wskazuje na pozycje liczby, która ma być przesunięta w prawo
				for (j = i; j > 0 && value < w[j-k]; j-=k) {
					w[j] = w[j-k];
				}
				w[j] = value; //wstawienie wartości
			}

			k = (k+1) / 2 - 1;
		}
	}


	static void selectionSort(int[] w) {
		//W kolejnych iteracjach szukamy najmniejszej wartości w zakresie <i, w.length)
		//Najmniejszą wartość wstawiamy na początek
		//Po x obiegach mamy x posortowanych elementów na początku
		for (int i = 0; i < w.length - 1; i++) {
			//Szukanie minimum
			int minIndex = i;
			for (int j = i; j < w.length; j++) {
				if (w[j] < w[minIndex]) minIndex = j;
			}

			//Jeśli minimum nie jest na i-tym miejscu, zamieniamy je z liczbą na tym miejscu
			if (i != minIndex) {
				int swap = w[i];
				w[i] = w[minIndex];
				w[minIndex] = swap;
			}
		}
	}

	static void heapSort(int [] w) {
		Heap heap = new Heap(w);
		for(int i = w.length - 1; i >= 0; i--) {
			w[i] = heap.extractMax();
		}
	}

	static void mergeSort(int[] w) {
		mergeSortRecursion(w, 0, w.length - 1);
	}
	private static void mergeSortRecursion(int[] w, int start, int end) {
		//Jeśli przysłany fragment tablicy jest dłuższy niż 1, dzielimy go na pół
		//i dla obu części wykonujemy mergeSort. Potem scalamy je algorytmem merge
		//Jeśli fragment ma długość 1 (end - start = 0 czyli end = start) nie robimy nic,
		//bo przecież taka podtablica nie może być nieuporządkowana
		if (end - start > 0) {
			int middle = (start + end)/2;

			mergeSortRecursion(w, start, middle); //sortujemy rekurencyjnie pierwszy fragment
			mergeSortRecursion(w, middle + 1, end); //sortujemy rekurencyjnie drugi fragment

			//w tym momencie oba fragmenty są posortowane, więc możemy je scalić
			merge(w, start, middle, end);
		}
	}
	private static void merge(int[] w, int start, int middle, int end) {
		//Algorytm scala dwie posortowane podtablice w jedną posortowaną

		//Tworzymy lewą podtablicę
		int length1 = middle - start + 1;
		int[] tab1 = new int[length1];
		for (int i = 0; i < tab1.length; i++) {
			tab1[i] = w[start + i];
		}

		//Tworzymy prawą podtablicę
		int length2 = end - middle;
		int[] tab2 = new int[length2];
		for (int i = 0; i < tab2.length; i++) {
			tab2[i] = w[middle + i + 1];
		}

		//Po jednym wskaźniku dla każdej podtablicy
		//Jeśli oba indeksy nie są jeszcze zbyt duże (większe lub równe length)
		//To porównujemy liczby na które pokazują te indeksy i wstawiamy mniejszą
		//Jeśli jeden z indeksów jest już za duży, to używamy tylko drugiego
		int i1 = 0;
		int i2 = 0;
		for (int k = start; k <= end; k++) {
			if (i1 < length1) {
				if (i2 < length2) w[k] = (tab1[i1] < tab2[i2]) ? tab1[i1++] : tab2[i2++];
				else w[k] = tab1[i1++];
			} else {
				w[k] = tab2[i2++];
			}
		}
	}

	static void quickSort(int[] w) {
		quickSortRecursion(w, 0, w.length - 1);
	}
	private static void quickSortRecursion(int[] w, int start, int end) {
		//Wybieramy pivot i sortujemy tak że po lewej są liczby <= pivot a po prawej >= pivot
		int pivot = w[(end + start)/2];
		int lewy = start; //Lewy wskaznik, idzie zawsze w prawo
		int prawy = end; //Prawy wskaznik, idzie zawsze w lewo

		//Warunek lewy <= prawy nie jest spełniony, gdy wskaźniki się "wyminą"
		while (lewy <= prawy) {
			while (w[lewy] < pivot) lewy++; //Po tej pętli lewy pokazuje na liczbę >= pivot
			while (w[prawy] > pivot) prawy--; //Po tej pętli prawy pokazuje na liczbę <= pivot

			if (lewy <= prawy) {
				int swap = w[lewy];
				w[lewy] = w[prawy];
				w[prawy] = swap;

				lewy++;
				prawy--;
			}
		}

		//Wykonujemy quicksort dla obu otrzymanych części tablicy
		//Ważne: punktem podziału nie jest pivot, tylko lewy/prawy
		if (prawy > start) quickSortRecursion(w, start, prawy);
		if (lewy < end) quickSortRecursion(w, lewy, end);
	}
}
